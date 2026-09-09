import {test,expect,auth,open} from './fixtures';
test('US-SP-AUTH-001 actual password login rejects invalid input then establishes authenticated session',async({page,context})=>{
 expect(auth.login_password,'fresh fixture must supply synthetic password').toBeTruthy();await context.clearCookies();await page.goto('/');await expect(page).toHaveURL(/\/login/);await page.locator('#pw').fill('incorrect-synthetic-password');await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page).toHaveURL(/\/login/);await expect(page.locator('#err')).toBeVisible();
 await page.locator('#pw').fill(auth.login_password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#msg')).toBeVisible();await expect(page).not.toHaveURL(/\/login/);const cookies=await context.cookies();expect(cookies.some(c=>c.name===auth.cookie_name&&c.httpOnly)).toBe(true);
});
test('US-SP-AUTH-LOGOUT sign out revokes browser access and redirects to login',async({page,context})=>{
 await context.clearCookies();await page.goto('/login');await page.locator('#pw').fill(auth.login_password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#msg')).toBeVisible();await open(page,'settings');await page.locator('[data-settings-section="system"]').click();await page.locator('#btnSignOut').click();await expect(page).toHaveURL(/\/login/);await page.goto('/');await expect(page).toHaveURL(/\/login/);
});
test('US-SP-AUTH-ANONYMOUS authenticated data APIs reject absent cookie',async({browser,page})=>{
 const c=await browser.newContext({baseURL:auth.base_url});try{for(const route of ['/api/sessions','/api/governance/users','/api/memory']){const r=await c.request.get(route);expect(r.status(),route).toBe(401);}}finally{await c.close();}
});
