from playwright.sync_api import sync_playwright
base='/mnt/data/rw_work'
with sync_playwright() as p:
 b=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
 page=b.new_page()
 errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
 print('read')
 s=open(base+'/information-ideas/index.html',encoding='utf-8').read()
 page.set_content(s,wait_until='domcontentloaded',timeout=60000)
 print('content loaded',page.title(),errors)
 page.get_by_role('button',name='Start Test').click(timeout=10000)
 print('started',page.locator('#question-counter').inner_text(), 'choices',page.locator('#answer-area .choice').count(), errors)
 page.locator('#answer-area .choice').first.click();page.locator('#next-btn').click()
 print('next',page.locator('#question-counter').inner_text(),errors)
 page.once('dialog',lambda d:d.dismiss());page.locator('#header-main-menu-btn').click()
 print('dialog works',errors)
 b.close()
