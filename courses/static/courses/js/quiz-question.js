const quizForm = document.getElementById("quiz-question-form");

if (quizForm) {
    quizForm.addEventListener("submit", function (event) {
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

        let unansweredQuestions =
            submitter.dataset.unansweredQuestions
                ? submitter.dataset.unansweredQuestions
                    .split(",")
                    .filter(Boolean)
                : [];

        const selectedChoice = quizForm.querySelector(
            'input[name="choice"]:checked'
        );

        const currentOrder = String(
            submitter.dataset.currentOrder || ""
        );

        if (selectedChoice) {
            unansweredQuestions = unansweredQuestions.filter(
                (questionNumber) =>
                    questionNumber !== currentOrder
            );
        }

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
        }
    });
}
