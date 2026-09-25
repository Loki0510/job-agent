import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from app.services.applicant import APPLICANT, answer_for_label
from app.services.resumes import resume_for

SUPPORTED_HOSTS=("greenhouse.io","lever.co","jobs.lever.co")

def _norm(value):
    return re.sub(r"\s+"," ",(value or "").strip().lower())

def _supported(url):
    host=(urlparse(url).hostname or "").lower()
    return any(host==x or host.endswith("."+x) for x in SUPPORTED_HOSTS)

async def _field_context(locator):
    try:
        field_id=await locator.get_attribute("id")
        if field_id:
            label=locator.page.locator(f'label[for="{field_id}"]')
            if await label.count():
                text=(await label.first.inner_text()).strip()
                if text:
                    return text
    except Exception:
        pass
    parts=[]
    for attr in ("name","placeholder","aria-label"):
        try:
            value=await locator.get_attribute(attr)
            if value: parts.append(value)
        except Exception:
            pass
    return " ".join(parts)

async def _question_context(locator):
    try:
        fieldset=locator.locator("xpath=ancestor::fieldset[1]")
        if await fieldset.count():
            legend=fieldset.locator("legend")
            if await legend.count():
                text=(await legend.first.inner_text()).strip()
                if text:
                    return text
    except Exception:
        pass
    try:
        preceding=locator.locator("xpath=preceding::label[1]")
        if await preceding.count():
            text=(await preceding.first.inner_text()).strip()
            if text and _norm(text) not in {"select","select...","yes","no"} and len(text)<600:
                return text
    except Exception:
        pass
    try:
        for depth in range(1,5):
            parent=locator.locator(f"xpath=ancestor::*[self::div or self::li][{depth}]")
            if await parent.count():
                text=(await parent.first.inner_text()).strip()
                simple=_norm(text)
                if text and simple not in {"select","select...","yes","no"} and len(text)<900:
                    return text
    except Exception:
        pass
    return await _field_context(locator)

async def _fill_text(input_el, context):
    q=_norm(context)
    value=None
    if "first name" in q:
        value=APPLICANT.first_name
    elif "last name" in q:
        value=APPLICANT.last_name
    elif "full name" in q or q=="name":
        value=APPLICANT.name
    elif "email" in q:
        value=APPLICANT.email
    elif "phone" in q or "mobile" in q:
        value=APPLICANT.phone
    elif "linkedin" in q:
        value=APPLICANT.linkedin
    elif ("current company" in q or q in {"org","organization","company"}) and APPLICANT.current_company:
        value=APPLICANT.current_company
    else:
        value=answer_for_label(context)
    if value:
        await input_el.fill(str(value))
        return True
    return False

async def _captcha_present(page):
    body=_norm(await page.locator("body").inner_text())
    if any(x in body for x in ("verify you are human","security check","hcaptcha")):
        return True
    for selector in ('iframe[src*="recaptcha"]','iframe[src*="hcaptcha"]','[class*="captcha"]'):
        if await page.locator(selector).count():
            return True
    return False

async def _select_known_choice(el, context, answer):
    if answer is None:
        return False
    typ=(await el.get_attribute("type") or "").lower()
    if typ=="radio":
        name=await el.get_attribute("name")
        page=el.page
        group=page.locator(f'input[type="radio"][name="{name}"]') if name else el
        for i in range(await group.count()):
            option=group.nth(i)
            option_text=_norm(await _field_context(option))
            value=_norm(await option.get_attribute("value") or "")
            if _norm(answer) in {option_text,value}:
                await option.check()
                return True
        return False
    if typ=="checkbox":
        label=_norm(await _field_context(el))
        if _norm(answer) in {"yes","true"} and ("yes" in label or not label):
            await el.check()
            return True
        return False
    tag=await el.evaluate("(e)=>e.tagName.toLowerCase()")
    if tag=="select":
        options=await el.locator("option").all_text_contents()
        target=next((x for x in options if _norm(x)==_norm(answer)),None)
        if target:
            await el.select_option(label=target)
            return True
        if str(answer).isdigit():
            years=int(answer)
            for x in options:
                m=re.search(r"(\d+)\s*[-–]\s*(\d+)",x)
                if m and int(m.group(1))<=years<=int(m.group(2)):
                    await el.select_option(label=x)
                    return True
                m=re.search(r"(\d+)\+",x)
                if m and years>=int(m.group(1)):
                    await el.select_option(label=x)
                    return True
        return False
    return False

async def inspect_and_fill(job, dry_run=True):
    url=job.get("apply_url") or ""
    if not _supported(url):
        return {"status":"blocked","reason":"unsupported application host","unknown_required":[]}

    resume=resume_for(job.get("resume_profile","java"))
    if not all([APPLICANT.name,APPLICANT.email,APPLICANT.phone,resume]):
        return {"status":"blocked","reason":"candidate contact or resume data missing","unknown_required":[]}

    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        page=await browser.new_page()
        try:
            await page.goto(url,wait_until="domcontentloaded",timeout=45000)
            captcha=await _captcha_present(page)
            if captcha and not dry_run:
                return {"status":"blocked","reason":"captcha or human verification detected","unknown_required":[]}

            files=page.locator('input[type="file"]')
            if await files.count():
                await files.first.set_input_files(resume)

            text_inputs=page.locator('input:not([type]), input[type="text"], input[type="email"], input[type="tel"], input[type="url"], textarea')
            for i in range(await text_inputs.count()):
                el=text_inputs.nth(i)
                try:
                    if not await el.is_visible() or await el.is_disabled():
                        continue
                    context=await _field_context(el)
                    await _fill_text(el,context)
                except Exception:
                    continue

            unknown=[]
            required=page.locator("input[required], textarea[required], select[required]")
            seen_choice_groups=set()
            for i in range(await required.count()):
                el=required.nth(i)
                try:
                    if not await el.is_visible() or await el.is_disabled():
                        continue
                    typ=(await el.get_attribute("type") or "").lower()
                    context=await _question_context(el)
                    answer=answer_for_label(context,job.get("company",""))
                    if typ=="radio":
                        name=await el.get_attribute("name") or context
                        if name in seen_choice_groups:
                            continue
                        seen_choice_groups.add(name)
                        if not await _select_known_choice(el,context,answer):
                            unknown.append(context or "required choice")
                        continue
                    if typ=="checkbox":
                        if not await el.is_checked() and not await _select_known_choice(el,context,answer):
                            unknown.append(context or "required checkbox")
                        continue
                    tag=await el.evaluate("(e)=>e.tagName.toLowerCase()")
                    if tag=="select":
                        value=await el.input_value()
                        if not value and not await _select_known_choice(el,context,answer):
                            unknown.append(context or "required select")
                        continue
                    value=await el.input_value()
                    if not value:
                        filled=await _fill_text(el,context)
                        if not filled and answer is not None:
                            await el.fill(str(answer))
                            filled=True
                        if not filled:
                            unknown.append(context or "required field")
                except Exception:
                    continue

            if unknown:
                return {
                    "status":"blocked",
                    "reason":"unknown required questions",
                    "unknown_required":sorted(set(unknown))[:20],
                    "captcha_detected":captcha,
                }

            if dry_run:
                return {
                    "status":"ready",
                    "reason":"form filled; submit intentionally skipped",
                    "unknown_required":[],
                    "captcha_detected":captcha,
                }

            buttons=page.get_by_role("button")
            for text in ("Submit application","Submit Application","Apply","Submit"):
                btn=buttons.get_by_text(text,exact=False)
                if await btn.count():
                    await btn.first.click()
                    await page.wait_for_timeout(1500)
                    post_captcha=await _captcha_present(page)
                    if post_captcha:
                        return {"status":"blocked","reason":"captcha or human verification detected at submit","unknown_required":[]}
                    return {"status":"submitted","reason":"submit clicked","unknown_required":[]}
            return {"status":"blocked","reason":"submit button not found","unknown_required":[]}
        finally:
            await browser.close()
