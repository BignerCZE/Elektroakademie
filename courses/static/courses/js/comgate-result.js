document.addEventListener("DOMContentLoaded", function () {
    window.ElektroakademieOrderDraft.clear();

    const status = document.getElementById("comgate-status");
    const refreshLink = document.getElementById("comgate-refresh");
    if (!refreshLink || !status.firstElementChild.hasAttribute("data-refresh")) {
        return;
    }

    const url = new URL(refreshLink.href);
    url.searchParams.set("fragment", "1");
    const interval = 3000;
    const deadline = performance.now() + 60000;

    function schedule() {
        if (performance.now() + interval < deadline) {
            window.setTimeout(refreshStatus, interval);
        }
    }

    async function refreshStatus() {
        const remaining = deadline - performance.now();
        if (remaining <= 0) {
            return;
        }

        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), Math.min(remaining, 5000));
        try {
            const response = await fetch(url, { signal: controller.signal });
            if (response.status === 404) {
                return;
            }
            if (response.ok) {
                const page = new DOMParser().parseFromString(await response.text(), "text/html");
                const next = page.querySelector("[data-comgate-status]");
                if (next && !next.isEqualNode(status.firstElementChild)) {
                    status.replaceChildren(next);
                }
                if (next && !next.hasAttribute("data-refresh")) {
                    refreshLink.parentElement.remove();
                    return;
                }
            }
        } catch {
            // A transient network failure leaves the manual refresh available.
        } finally {
            window.clearTimeout(timeout);
        }
        schedule();
    }

    schedule();
});
