document.addEventListener("DOMContentLoaded", () => {
    const dialogs = document.querySelectorAll(".portal-dialog");
    const activeDialog = document.getElementById("portal-active-quiz-dialog");
    const activeFrame = document.getElementById("portal-active-quiz-frame");
    let leavingQuiz = false;

    function popupURL(href) {
        const url = new URL(href, location.href);
        url.searchParams.set("popup", "1");
        return url.href;
    }
    function leaveActiveQuiz() {
        if (leavingQuiz) return;
        if (!confirm("Opravdu chcete opustit test? Rozpracovaný test zůstane uložen a můžete v něm pokračovat později.")) return;
        const form = activeFrame?.contentDocument?.getElementById("quiz-question-form");
        if (!form) { activeDialog.close(); location.reload(); return; }
        leavingQuiz = true;
        const button = form.ownerDocument.createElement("button");
        button.type = "submit";
        button.name = "leave_test";
        button.value = "1";
        button.hidden = true;
        form.append(button);
        form.requestSubmit(button);
    }

    const historyDialog = document.getElementById("portal-history-dialog");
    const historyList = historyDialog?.querySelector("[data-portal-history-list]");
    const reviewPane = historyDialog?.querySelector("[data-portal-review-pane]");
    const historyTitle = document.getElementById("portal-history-title");
    const historySubtitle = document.getElementById("portal-history-subtitle");
    const originalSubtitle = historySubtitle?.textContent;
    let controller;
    let generation = 0;
    let returnLink;

    function showHistory() {
        generation++;
        controller?.abort();
        if (!historyDialog) return;
        historyList.hidden = false;
        reviewPane.hidden = true;
        reviewPane.replaceChildren();
        reviewPane.removeAttribute("aria-busy");
        historyTitle.textContent = "Historie testů";
        historySubtitle.textContent = originalSubtitle;
        historyDialog.querySelectorAll("[data-portal-history-back]").forEach(button => { button.hidden = true; });
    }

    function openDialog(dialog, trigger) {
        if (!dialog || dialog.open) return;
        const frame = dialog.querySelector("[data-portal-video-frame]");
        if (frame && !window.EACookies?.mediaAllowed()) {
            window.EACookies?.open();
            return;
        }
        if (dialog === historyDialog) { showHistory(); returnLink = null; }
        if (dialog === activeDialog) leavingQuiz = false;
        if (frame) {
            const iframe = document.createElement("iframe");
            iframe.src = "https://www.youtube-nocookie.com/embed/J_eSsfNwDVw?autoplay=1&rel=0&modestbranding=1";
            iframe.title = "Výukové video";
            iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
            iframe.referrerPolicy = "strict-origin-when-cross-origin";
            iframe.allowFullscreen = true;
            frame.replaceChildren(iframe);
        }
        dialog.showModal();
        document.body.classList.add("portal-dialog-open");
        if (dialog.querySelector(".certificate-document")) window.fitCertificates?.();
        dialog.querySelector("[data-portal-close]")?.focus();
        dialog.addEventListener("close", () => {
            frame?.replaceChildren();
            if (dialog === historyDialog) showHistory();
            document.body.classList.remove("portal-dialog-open");
            trigger.focus();
        }, {once: true});
    }

    async function showReview(link) {
        if (!historyDialog || !reviewPane) return;
        const url = new URL(link.href, window.location.href);
        if (url.origin !== window.location.origin) return;
        if (!historyDialog.open) openDialog(historyDialog, link);
        if (historyList.contains(link)) returnLink = link;
        const current = ++generation;
        controller?.abort();
        controller = new AbortController();
        historyList.hidden = true;
        reviewPane.hidden = false;
        reviewPane.textContent = "Načítání odpovědí…";
        reviewPane.setAttribute("aria-busy", "true");
        historyTitle.textContent = "Kontrola testu";
        historySubtitle.textContent = "Procházení jednotlivých otázek a odpovědí";
        historyDialog.querySelector("[data-portal-history-back]").hidden = false;
        url.searchParams.set("fragment", "1");
        try {
            const response = await fetch(url, {credentials: "same-origin", cache: "no-store", signal: controller.signal});
            if (!response.ok || response.headers.get("X-Quiz-Review-Fragment") !== "1") throw new Error("Review unavailable");
            const html = await response.text();
            if (current !== generation || !historyDialog.open) return;
            // This is an escaped, server-rendered fragment from the authenticated
            // same-origin review endpoint; no browser-supplied HTML is accepted.
            reviewPane.innerHTML = html;
            reviewPane.scrollTop = 0;
            const heading = reviewPane.querySelector(".quiz-card h1");
            if (heading) { heading.tabIndex = -1; heading.focus({preventScroll: true}); }
        } catch (error) {
            if (error.name === "AbortError" || current !== generation || !historyDialog.open) return;
            const message = document.createElement("p");
            message.setAttribute("role", "alert");
            message.textContent = "Odpovědi se nepodařilo načíst. Zkuste to znovu z historie nebo se znovu přihlaste.";
            reviewPane.replaceChildren(message);
        } finally {
            if (current === generation) reviewPane.removeAttribute("aria-busy");
        }
    }

    document.querySelectorAll("[data-portal-open]").forEach(trigger => {
        trigger.addEventListener("click", () => openDialog(document.getElementById(trigger.dataset.portalOpen), trigger));
    });
    document.addEventListener("click", event => {
        const activeLink = event.target.closest("a[data-portal-active-quiz]");
        if (activeLink && activeDialog && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
            event.preventDefault();
            openDialog(activeDialog, activeLink);
            activeFrame.src = popupURL(activeLink.href);
            return;
        }
        const link = event.target.closest("a[data-portal-review]");
        if (link && historyDialog && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
            event.preventDefault();
            showReview(link);
            return;
        }
        const back = event.target.closest("[data-portal-history-back]");
        if (back && historyDialog?.contains(back)) {
            showHistory();
            (returnLink || historyList).focus({preventScroll: true});
        }
    });
    dialogs.forEach(dialog => {
        dialog.querySelector("[data-portal-close]")?.addEventListener("click", () => {
            if (dialog === activeDialog) leaveActiveQuiz(); else dialog.close();
        });
        dialog.addEventListener("cancel", event => {
            if (dialog === activeDialog) { event.preventDefault(); leaveActiveQuiz(); }
        });
        dialog.addEventListener("click", event => {
            if (event.target !== dialog) return;
            const bounds = dialog.getBoundingClientRect();
            if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) {
                if (dialog === activeDialog) leaveActiveQuiz(); else dialog.close();
            }
        });
    });
    document.addEventListener("submit", event => {
        const form = event.target.closest("form[data-portal-start-quiz]");
        if (!form || !activeDialog) return;
        form.target = activeFrame.name;
        form.action = popupURL(form.action);
        openDialog(activeDialog, event.submitter || form.querySelector("button"));
    });
    window.addEventListener("message", event => {
        if (!activeFrame || event.source !== activeFrame.contentWindow || event.origin !== location.origin || !activeDialog?.open) return;
        if (event.data?.type !== "ea-quiz-left" && event.data?.type !== "ea-quiz-completed") return;
        if (event.data.type === "ea-quiz-completed" && typeof event.data.review_url === "string") {
            const url = new URL(event.data.review_url, location.href);
            if (url.origin === location.origin) {
                try { sessionStorage.setItem("ea-pending-quiz-review", url.pathname); } catch (_) { /* The overview still refreshes if storage is disabled. */ }
            }
        }
        activeDialog.close();
        location.reload();
    });
    let pending;
    try { pending = sessionStorage.getItem("ea-pending-quiz-review"); sessionStorage.removeItem("ea-pending-quiz-review"); } catch (_) { /* Optional review reopening. */ }
    if (pending) {
        const link = Array.from(document.querySelectorAll("a[data-portal-review]")).find(item => new URL(item.href).pathname === pending);
        if (link) showReview(link);
    }

});
