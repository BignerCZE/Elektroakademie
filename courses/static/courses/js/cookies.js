(function () {
    "use strict";
    if (window.self !== window.top) return;
    const config = JSON.parse(document.getElementById("ea-cookie-config").textContent);
    const banner = document.getElementById("cookie-banner");
    const options = document.getElementById("cookie-options");
    const form = document.getElementById("cookie-form");
    const consentPanel = document.getElementById("cookie-consent-panel");
    const infoPanel = document.getElementById("cookie-info-panel");
    const dialog = document.getElementById("cookie-dialog");
    let infoReturnFocus = null;
    let infoWasOpen = false;
    function showPanel(information) {
        consentPanel.hidden = information;
        infoPanel.hidden = !information;
        dialog.setAttribute("aria-label", information ? "Cookies a vaše soukromí" : "Nastavení cookies");
        if (information) dialog.removeAttribute("aria-labelledby");
        else dialog.setAttribute("aria-labelledby", "cookie-title");
        dialog.scrollTop = 0;
    }
    let choice = config.preferences;
    let loaded = false;
    let returnFocus = null;
    const channel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("ea-cookie-choice") : null;
    if (channel) channel.onmessage = () => { window["ga-disable-" + config.measurementId] = true; location.reload(); };
    const id = config.measurementId;
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    function track(name, params) {
        if (loaded && choice && choice.analytics) gtag("event", name, params || {});
    }
    function activate() {
        if (!id || !choice || !choice.analytics || loaded) return;
        loaded = true;
        window["ga-disable-" + id] = false;
        gtag("consent", "default", {analytics_storage:"granted", ad_storage:"denied", ad_user_data:"denied", ad_personalization:"denied"});
        gtag("js", new Date());
        // Never transmit raw URLs, query strings, document titles or referrers.
        gtag("config", id, {send_page_view:false, allow_google_signals:false,
            allow_ad_personalization_signals:false, cookie_expires:15552000,
            page_location:location.origin + "/" + config.page + "/", page_referrer:"", page_title:config.page});
        const script = document.createElement("script");
        script.async = true;
        script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
        document.head.appendChild(script);
        track("page_view");
        if (config.orderCreated) track("order_created");
        if (config.page === "register") track("checkout_step", {step:Number(document.body.dataset.checkoutStep || 1)});
    }
    function setDetails(expanded) {
        options.hidden = !expanded;
        const toggle = document.getElementById("cookie-settings-toggle");
        toggle.setAttribute("aria-expanded", String(expanded));
        toggle.textContent = expanded ? "Skrýt nastavení" : "Nastavení";
    }
    function open() {
        returnFocus = document.activeElement;
        showPanel(false);
        banner.hidden = false;
        setDetails(true);
        document.getElementById("cookie-analytics").checked = !!(choice && choice.analytics);
        document.getElementById("cookie-media").checked = !!(choice && choice.media);
        consentPanel.querySelector("button").focus();
    }
    function close() {
        if (!infoPanel.hidden && infoWasOpen) {
            showPanel(false);
            if (infoReturnFocus && infoReturnFocus.focus) infoReturnFocus.focus();
            return;
        }
        banner.hidden = true;
        if (returnFocus && returnFocus.focus) returnFocus.focus();
    }
    document.querySelectorAll("[data-cookie-info]").forEach(el => el.addEventListener("click", event => {
        event.preventDefault();
        infoReturnFocus = document.activeElement;
        infoWasOpen = !banner.hidden;
        if (!infoWasOpen) returnFocus = document.activeElement;
        showPanel(true);
        banner.hidden = false;
        infoPanel.querySelector("button").focus();
    }));
    document.querySelectorAll("[data-cookie-back]").forEach(el => el.addEventListener("click", () => open()));
    document.querySelectorAll("[data-cookie-close]").forEach(el => el.addEventListener("click", close));
    document.addEventListener("keydown", event => {
        if (banner.hidden) return;
        if (event.key === "Escape") { event.preventDefault(); close(); return; }
        if (event.key !== "Tab") return;
        const targets = Array.from(banner.querySelectorAll("button:not(:disabled), a[href], input:not(:disabled), [tabindex='0']"))
            .filter(el => el.getClientRects().length > 0);
        const first = targets[0], last = targets[targets.length - 1];
        if (!first) return;
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    window.EACookies = {open:open, mediaAllowed:function () {return !!(choice && choice.media);}, track:track};
    document.querySelectorAll("[data-cookie-settings]").forEach(el => el.addEventListener("click", e => {e.preventDefault();open();}));
    document.querySelectorAll("[data-cookie-choice]").forEach(el => el.addEventListener("click", async () => {
        const action = el.dataset.cookieChoice;
        if (action === "settings") { setDetails(options.hidden); return; }
        const selected = {
            analytics:action === "all" || (action === "save" && document.getElementById("cookie-analytics").checked),
            media:action === "all" || (action === "save" && document.getElementById("cookie-media").checked)
        };
        form.querySelectorAll("button").forEach(b => {b.disabled=true;});
        try {
            const response = await fetch(form.action, {method:"POST", credentials:"same-origin",
                headers:{"Content-Type":"application/json", "X-CSRFToken":form.querySelector("[name=csrfmiddlewaretoken]").value}, body:JSON.stringify(selected)});
            if (!response.ok) throw new Error();
            const mustReload = (loaded && !selected.analytics) || (choice && choice.media && !selected.media);
            choice = await response.json();
            if (channel) channel.postMessage("changed");
            if (!choice.analytics) {
                window["ga-disable-" + id] = true;
                document.cookie.split(";").forEach(item => {
                    const name = item.split("=")[0].trim();
                    if (!/^_ga(?:_|$)|^_gid$|^_gat/.test(name)) return;
                    const parts = location.hostname.split(".");
                    document.cookie = name + "=; Max-Age=0; path=/";
                    for(let i=0;i<parts.length-1;i++) document.cookie = name+"=; Max-Age=0; path=/; domain=."+parts.slice(i).join(".");
                });
            }
            // Reload stops any previously loaded Google scripts and YouTube frames immediately.
            if (mustReload) { location.reload(); return; }
            form.querySelectorAll("button").forEach(b => {b.disabled=false;});
            close();
            activate();
        } catch (_) {
            document.getElementById("cookie-status").textContent="Volbu se nepodařilo uložit. Zkuste to znovu. Volitelné služby se nezapnou.";
            form.querySelectorAll("button").forEach(b => {b.disabled=false;});
        }
    }));
    banner.hidden = !!choice;
    if (!choice) { returnFocus = document.activeElement; consentPanel.querySelector('[data-cookie-choice="all"]').focus(); }
    activate();
    if (config.page === "register") {
        new MutationObserver(() => track("checkout_step", {step:Number(document.body.dataset.checkoutStep || 1)}))
            .observe(document.body, {attributes:true, attributeFilter:["data-checkout-step"]});
    }
    document.addEventListener("click", e => {
        const link = e.target.closest("a");
        if (link && config.page && new URL(link.href, location.href).pathname === "/registrace/") track("begin_checkout");
    });
}());
