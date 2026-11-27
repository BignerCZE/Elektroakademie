const returnLink = document.getElementById("activation-return-link");
const countdown = document.getElementById("activation-return-countdown");

if (returnLink && countdown) {
    const seconds = countdown.querySelector("strong");
    const deadline = Date.now() + 15000;
    countdown.hidden = false;

    const timer = window.setInterval(() => {
        const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        seconds.textContent = `${remaining} s`;
        if (remaining === 0) {
            window.clearInterval(timer);
            window.location.replace(returnLink.href);
        }
    }, 1000);
}
