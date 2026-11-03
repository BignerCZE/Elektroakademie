const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/courses/js/cookies.js'), 'utf8');
function setup(preferences=null, measurementId='G-TEST', failure=false) {
    const buttons = ['all','none','save','settings'].map(action => ({dataset:{cookieChoice:action}, addEventListener:(_,fn)=>buttons.find(b=>b.dataset.cookieChoice===action).click=fn, focus(){}}));
    const elements = {
        'ea-cookie-config':{textContent:JSON.stringify({preferences,measurementId,page:'index'})},
        'cookie-banner':{hidden:true,querySelector:()=>buttons[0]},
        'cookie-consent-panel':{hidden:false,querySelector:()=>buttons[0]}, 'cookie-info-panel':{hidden:true,querySelector:()=>buttons[0]}, 'cookie-dialog':{setAttribute(){},removeAttribute(){}},
        'cookie-settings-toggle':{setAttribute(){}}, 'cookie-options':{hidden:true}, 'cookie-analytics':{checked:false}, 'cookie-media':{checked:false}, 'cookie-status':{},
        'cookie-form':{action:'/cookies/souhlas/',querySelector:()=>({value:'csrf-token'}),querySelectorAll:()=>buttons}
    };
    const infoLink={addEventListener:(_,fn)=>{infoLink.click=fn;}};
    const closeButton={addEventListener:(_,fn)=>{closeButton.click=fn;}};
    const scripts=[];let reloads=0;
    const document={getElementById:id=>elements[id],querySelectorAll:selector=>selector==='[data-cookie-choice]'?buttons:selector==='[data-cookie-info]'?[infoLink]:selector==='[data-cookie-close]'?[closeButton]:[],
        head:{appendChild:s=>scripts.push(s)},createElement:()=>({}),cookie:'_ga=1',body:{dataset:{}},addEventListener(){}};
    const window={dataLayer:[]};window.self=window;window.top=window;
    const context={window,document,URL,location:{origin:'https://example.cz',hostname:'example.cz',reload:()=>reloads++},
        fetch:async(url,options)=>({ok:!failure,json:async()=>JSON.parse(options.body)})};
    vm.runInNewContext(source,context);
    return {window,elements,scripts,buttons,infoLink,closeButton,get reloads(){return reloads;}};
}
test('no consent: no Google script or events',()=>{const x=setup();assert.equal(x.scripts.length,0);assert.equal(x.window.dataLayer.length,0);assert.equal(x.elements['cookie-banner'].hidden,false);});
test('media only does not load Analytics',()=>{const x=setup({analytics:false,media:true});assert.equal(x.scripts.length,0);assert.equal(x.window.EACookies.mediaAllowed(),true);});
test('analytics consent loads one script with sanitized page metadata',()=>{const x=setup({analytics:true,media:false});assert.equal(x.scripts.length,1);const config=x.window.dataLayer.find(v=>v[0]==='config')[2];assert.equal(config.page_location,'https://example.cz/index/');assert.equal(config.page_referrer,'');assert.equal(config.allow_google_signals,false);});
test('private page never loads Analytics even with consent',()=>{assert.equal(setup({analytics:true,media:true},'').scripts.length,0);});
test('reject saves without loading services or reloading form',async()=>{const x=setup();await x.buttons[1].click();assert.equal(x.scripts.length,0);assert.equal(x.reloads,0);assert.equal(x.elements['cookie-banner'].hidden,true);});
test('accept starts Analytics after successful save',async()=>{const x=setup();await x.buttons[0].click();assert.equal(x.scripts.length,1);assert.equal(x.reloads,0);});
test('failed save does not start Analytics',async()=>{const x=setup(null,'G-TEST',true);await x.buttons[0].click();assert.equal(x.scripts.length,0);assert.match(x.elements['cookie-status'].textContent,/nepodařilo/);});
test('withdrawal disables Analytics and reloads to unload trackers',async()=>{const x=setup({analytics:true,media:true});await x.buttons[1].click();assert.equal(x.window['ga-disable-G-TEST'],true);assert.equal(x.reloads,1);});

test('information opens in the same overlay without enabling tracking',()=>{
    const x=setup({analytics:false,media:false});
    x.infoLink.click({preventDefault(){}});
    assert.equal(x.elements['cookie-banner'].hidden,false);
    assert.equal(x.elements['cookie-info-panel'].hidden,false);
    assert.equal(x.elements['cookie-consent-panel'].hidden,true);
    assert.equal(x.scripts.length,0);
    x.window.EACookies.open();
    assert.equal(x.elements['cookie-info-panel'].hidden,true);
    assert.equal(x.elements['cookie-consent-panel'].hidden,false);
});

test('settings toggles details and preserves unsaved choices',async()=>{
    const x=setup();
    assert.equal(x.elements['cookie-options'].hidden,true);
    await x.buttons[3].click();
    assert.equal(x.elements['cookie-options'].hidden,false);
    x.elements['cookie-analytics'].checked=true;
    await x.buttons[3].click();
    assert.equal(x.elements['cookie-options'].hidden,true);
    await x.buttons[3].click();
    assert.equal(x.elements['cookie-analytics'].checked,true);
    assert.equal(x.scripts.length,0);
});
test('footer API opens stored preferences directly',()=>{
    const x=setup({analytics:false,media:true});x.window.EACookies.open();
    assert.equal(x.elements['cookie-options'].hidden,false);
    assert.equal(x.elements['cookie-media'].checked,true);
});
test('closing without decision leaves optional services disabled',()=>{
    const x=setup();x.closeButton.click();
    assert.equal(x.elements['cookie-banner'].hidden,true);
    assert.equal(x.scripts.length,0);
    assert.equal(x.window.EACookies.mediaAllowed(),false);
});
