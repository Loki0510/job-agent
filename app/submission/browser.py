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
                return (await label.first.inner_text()).strip()
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
    if value:
        await input_el.fill(value)
        return True
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
            body=_norm(await page.locator("body").inner_text())
            if any(x in body for x in ("captcha","verify you are human","security check")):
                return {"status":"blocked","reason":"captcha or human verification detected","unknown_required":[]}

            for selector in ('iframe[src*="recaptcha"]','iframe[src*="hcaptcha"]','[class*="captcha"]'):
                if await page.locator(selector).count():
                    return {"status":"blocked","reason":"captcha detected","unknown_required":[]}

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
            for i in range(await required.count()):
                el=required.nth(i)
                try:
                    if not await el.is_visible() or await el.is_disabled():
                        continue
                    typ=(await el.get_attribute("type") or "").lower()
                    context=await _field_context(el)
                    answer=answer_for_label(context,job.get("company",""))
                    if typ in ("radio","checkbox"):
                        if answer is None:
                            unknown.append(context or "required choice")
                        continue
                    tag=await el.evaluate("(e)=>e.tagName.toLowerCase()")
                    if tag=="select":
                        if answer is None:
                            unknown.append(context or "required select")
                        else:
                            options=await el.locator("option").all_text_contents()
                            target=next((x for x in options if _norm(x)==_norm(answer)),None)
                            if target: await el.select_option(label=target)
                            else: unknown.append(context or "required select")
                        continue
                    value=await el.input_value()
                    if not value and answer is not None:
                        await el.fill(answer)
                    elif not value:
                        unknown.append(context or "required field")
                except Exception:
                    continue

            if unknown:
                return {"status":"blocked","reason":"unknown required questions","unknown_required":sorted(set(unknown))[:20]}

            if dry_run:
                return {"status":"ready","reason":"form filled; submit intentionally skipped","unknown_required":[]}

            buttons=page.get_by_role("button")
            for text in ("Submit application","Submit Application","Apply","Submit"):
                btn=buttons.get_by_text(text,exact=False)
                if await btn.count():
                    await btn.first.click()
                    await page.wait_for_timeout(1500)
                    return {"status":"submitted","reason":"submit clicked","unknown_required":[]}
            return {"status":"blocked","reason":"submit button not found","unknown_required":[]}
        finally:
            await browser.close()
