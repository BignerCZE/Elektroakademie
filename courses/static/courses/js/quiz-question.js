const quizForm = document.getElementById("quiz-question-form");

if (quizForm) {
    const submitButton = quizForm.querySelector('[data-submit-test="true"]');
    const progress = document.getElementById("quiz-answer-progress");

    function getUnansweredQuestions() {
        const unanswered = (submitButton.dataset.unansweredQuestions || "")
            .split(",").filter(Boolean);
        const currentOrder = submitButton.dataset.currentOrder;
        const selectedChoice = quizForm.querySelector('input[name="choice"]:checked');
        const otherUnanswered = unanswered.filter(number => number !== currentOrder);
        if (!selectedChoice) {
            otherUnanswered.push(currentOrder);
        }
        return otherUnanswered;
    }

    function updateSubmissionState() {
        const unanswered = getUnansweredQuestions();
        const total = Number(submitButton.dataset.totalQuestions);
        submitButton.hidden = total === 0 || unanswered.length > 0;
        progress.textContent = `Zodpovězeno ${total - unanswered.length} z ${total}`;
    }

    quizForm.addEventListener("change", updateSubmissionState);
    updateSubmissionState();

    let isSubmitting = false;

    window.addEventListener("pageshow", () => { isSubmitting = false; });

    quizForm.addEventListener("submit", function (event) {
        if (isSubmitting) {
            event.preventDefault();
            return;
        }
        const submitter = event.submitter;

        if (!submitter) {
            return;
        }

        if (submitter.dataset.leaveTest === "true") {
            const confirmed = confirm(
                "Opravdu chcete opustit test? " +
                "Rozpracovaný test zůstane uložen " +
                "a budete v něm moci pokračovat později."
            );

            if (!confirmed) {
                event.preventDefault();
            }

            return;
        }

        if (submitter.dataset.submitTest !== "true") {
            return;
        }

        const unansweredQuestions = getUnansweredQuestions();

        if (unansweredQuestions.length > 0) {
            event.preventDefault();

            alert(
                "Test nelze odeslat.\n\n" +
                "Doplňte odpovědi u otázek:\n\n" +
                unansweredQuestions.join(", ")
            );

            return;
        }

        if (!confirm(
            "Máte vyplněné všechny otázky. " +
            "Opravdu chcete test odeslat?"
        )) {
            event.preventDefault();
            return;
        }

        isSubmitting = true;
    });
}
