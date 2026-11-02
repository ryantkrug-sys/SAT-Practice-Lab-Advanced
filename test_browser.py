from playwright.sync_api import sync_playwright
base='/mnt/data/rw_work'
with sync_playwright() as p:
 b=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
 for d in ['information-ideas','craft-structure','expression-ideas','standard-conventions']:
  page=b.new_page();page.set_default_timeout(5000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(open(base+'/'+d+'/index.html',encoding='utf-8').read(),wait_until='domcontentloaded',timeout=60000)
  page.get_by_role('button',name='Start Test').click()
  active=page.locator('#test-screen').inner_text()
  assert 'Correct answer' not in active and 'Answer explanation' not in active and 'Question ID:' not in active
  for i in range(30):
   page.locator('#answer-area .choice').first.click();page.locator('#next-btn').click()
   if i<29: page.wait_for_function(f"document.querySelector('#question-counter').textContent === 'Question {i+2} of 30'")
  assert page.locator('#review-list .review').count()==30 and page.locator('#review-list .explanation').count()==30
  assert '/ 89' in page.locator('#overall-stats').inner_text()
  dialogs=[];page.once('dialog',lambda dialog:(dialogs.append(dialog.message),dialog.dismiss()));page.locator('#header-main-menu-btn').click()
  assert dialogs and 'Are you sure' in dialogs[0]
  print(d,'PASS: 30 questions, 30 explanations, confirmation, no JS errors',len(errors))
  assert not errors,errors;page.close()
 page=b.new_page();page.set_content(open(base+'/index.html',encoding='utf-8').read(),wait_until='domcontentloaded')
 for d in ['information-ideas','craft-structure','expression-ideas','standard-conventions']:
  page.locator('#domain').select_option(d);assert not page.locator('#start').is_disabled()
 print('Main menu dropdown PASS: all four Reading & Writing domains enabled')
 b.close()
