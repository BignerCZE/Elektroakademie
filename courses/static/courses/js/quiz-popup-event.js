const quizEvent = document.getElementById("quiz-popup-event");
if (quizEvent && window.parent !== window) {
    window.parent.postMessage(JSON.parse(quizEvent.textContent), window.location.origin);
}
