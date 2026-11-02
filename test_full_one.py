from playwright.sync_api import sync_playwright
base='/mnt/data/rw_work'
with sync_playwright() as p:
 b=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
 page=b.new_page(); page.set_default_timeout(5000); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(open(base+'/expression-ideas/index.html',encoding='utf-8').read(),wait_until='domcontentloaded',timeout=60000)
 page.get_by_role('button',name='Start Test').click()
 for i in range(30):
  page.locator('#answer-area .choice').first.click()
  page.locator('#next-btn').click()
  if i<29: page.wait_for_function(f"document.querySelector('#question-counter').textContent === 'Question {i+2} of 30'")
 print('finished loop')
 page.wait_for_selector('#results:not(.hidden)')
 print('results',page.locator('#review-list .review').count(),page.locator('#review-list .explanation').count(),page.locator('#overall-stats').inner_text(), 'errors',errors)
 print('longest explanation rendered',page.locator('#review-list .explanation').evaluate_all('(els)=>Math.max(...els.map(e=>e.scrollHeight-e.clientHeight))'))
 b.close()
