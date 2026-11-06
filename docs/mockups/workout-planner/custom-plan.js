const exercisesByGoalAndLevel = {
  strength: {
    beginner: ["Goblet squat", "Incline push-up", "Seated cable row", "Glute bridge", "Dumbbell Romanian deadlift", "Machine chest press"],
    intermediate: ["Barbell squat", "Bench press", "Lat pulldown", "Romanian deadlift", "Overhead press", "Cable row"],
    advanced: ["Trap-bar deadlift", "Barbell bench press", "Weighted pull-up", "Bulgarian split squat", "Front squat", "Pendlay row"]
  },
  muscle: {
    beginner: ["Leg press", "Dumbbell bench press", "Lat pulldown", "Leg curl", "Goblet squat", "Seated cable row"],
    intermediate: ["Incline dumbbell press", "Chest-supported row", "Hip thrust", "Leg press", "Lateral raise", "Romanian deadlift"],
    advanced: ["Barbell bench press", "Weighted pull-up", "Front squat", "Barbell hip thrust", "T-bar row", "Nordic hamstring curl"]
  },
  fitness: {
    beginner: ["Box squat", "Wall push-up", "Step-up", "Dead bug", "Dumbbell row", "Glute bridge"],
    intermediate: ["Goblet squat", "Dumbbell push press", "Reverse lunge", "Cable row", "Mountain climber", "Romanian deadlift"],
    advanced: ["Front squat", "Dumbbell push press", "Walking lunge", "Renegade row", "Barbell deadlift", "Pull-up"]
  }
};

const exercisesByEquipment = {
  dumbbells: {
    beginner: ["Goblet squat", "Dumbbell floor press", "One-arm dumbbell row", "Dumbbell glute bridge", "Dumbbell Romanian deadlift", "Dumbbell shoulder press"],
    intermediate: ["Dumbbell front squat", "Dumbbell bench press", "Single-arm dumbbell row", "Dumbbell Romanian deadlift", "Dumbbell reverse lunge", "Dumbbell shoulder press"],
    advanced: ["Dumbbell Bulgarian split squat", "Dumbbell incline press", "Renegade row", "Single-leg dumbbell RDL", "Dumbbell thruster", "Dumbbell snatch"]
  },
  bodyweight: {
    beginner: ["Chair squat", "Wall push-up", "Glute bridge", "Bird dog", "Step-up", "Knee plank"],
    intermediate: ["Reverse lunge", "Push-up", "Single-leg glute bridge", "Pike push-up", "Mountain climber", "Side plank"],
    advanced: ["Bulgarian split squat", "Decline push-up", "Single-leg hip hinge", "Pistol squat progression", "Pike push-up", "Hollow hold"]
  },
  bands: {
    beginner: ["Banded squat", "Band chest press", "Band row", "Band glute bridge", "Banded hip hinge", "Band pull-apart"],
    intermediate: ["Banded split squat", "Standing band press", "Single-arm band row", "Banded good morning", "Lateral band walk", "Band face pull"],
    advanced: ["Banded squat", "Single-arm band press", "Banded single-leg RDL", "High-anchor band row", "Banded reverse lunge", "Band-resisted push-up"]
  }
};

const goalLabels = {
  strength: "Get stronger",
  muscle: "Build muscle",
  fitness: "Improve fitness"
};

const experienceLabels = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced"
};

const equipmentLabels = {
  "full-gym": "Full gym",
  dumbbells: "Dumbbells",
  bodyweight: "Bodyweight only",
  bands: "Resistance bands"
};

const form = document.querySelector("#custom-plan-form");
const createButton = document.querySelector("#create-button");
const loadingNotice = document.querySelector("#custom-loading");
const errorNotice = document.querySelector("#custom-error");
const resultPanel = document.querySelector("#custom-result");
const resultTitle = document.querySelector("#result-title");
const resultSummary = document.querySelector("#result-summary");
const customWorkouts = document.querySelector("#custom-workouts");
let isBusy = false;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function getReps(goal, experience) {
  if (goal === "strength") {
    return experience === "advanced" ? "3-5" : experience === "intermediate" ? "4-6" : "6-8";
  }
  if (goal === "fitness") return experience === "advanced" ? "8-12" : "10-15";
  return experience === "advanced" ? "6-10" : "8-12";
}

function getSessions(preferences) {
  const exercises = preferences.equipment === "full-gym"
    ? exercisesByGoalAndLevel[preferences.goal][preferences.experience]
    : exercisesByEquipment[preferences.equipment][preferences.experience];
  const sets = preferences.experience === "beginner" ? 2 : preferences.experience === "intermediate" ? 3 : 4;
  const reps = getReps(preferences.goal, preferences.experience);

  return Array.from({ length: preferences.days }, (_, sessionIndex) => {
    const sessionExercises = Array.from({ length: 4 }, (_, exerciseIndex) => {
      const index = (sessionIndex * 2 + exerciseIndex) % exercises.length;
      return exercises[index];
    });
    const rows = sessionExercises.map((exercise) => `
      <tr><td>${escapeHtml(exercise)}</td><td>${sets}</td><td>${reps}</td></tr>`).join("");
    return `
      <article class="workout-card">
        <header class="workout-card-header">
          <div class="workout-card-title">
            <span class="workout-index">${String(sessionIndex + 1).padStart(2, "0")}</span>
            <div class="workout-name"><strong>${escapeHtml(preferences.experienceLabel)} ${sessionIndex % 2 === 0 ? "A" : "B"}</strong><span>Session ${sessionIndex + 1}</span></div>
          </div>
          <span class="workout-duration">${escapeHtml(equipmentLabels[preferences.equipment])}</span>
        </header>
        <table class="exercise-table">
          <thead><tr><th>Exercise</th><th>Sets</th><th>Reps</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </article>`;
  }).join("");
}

function showError(message) {
  errorNotice.innerHTML = `<span class="message-icon" aria-hidden="true">!</span><span>${escapeHtml(message)}</span>`;
  errorNotice.hidden = false;
}

function validateForm() {
  let valid = form.reportValidity();
  const days = Number(form.elements.days.value);
  if (!Number.isInteger(days) || days < 1 || days > 7) {
    form.elements.days.setCustomValidity("Choose between 1 and 7 workout days.");
    form.elements.days.reportValidity();
    valid = false;
  } else {
    form.elements.days.setCustomValidity("");
  }
  return valid;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isBusy || !validateForm()) return;

  const data = new FormData(form);
  const preferences = {
    title: data.get("planName"),
    goal: data.get("goal"),
    experience: data.get("experience"),
    experienceLabel: experienceLabels[data.get("experience")],
    equipment: data.get("equipment"),
    days: Number(data.get("days")),
    notes: data.get("notes")
  };

  isBusy = true;
  createButton.disabled = true;
  createButton.querySelector(".button-label").textContent = "Creating your plan...";
  loadingNotice.hidden = false;
  errorNotice.hidden = true;
  resultPanel.hidden = true;
  await new Promise((resolve) => window.setTimeout(resolve, 850));

  try {
    if (new URLSearchParams(window.location.search).has("simulateError")) {
      throw new Error("We couldn't build your plan just now. Please try again.");
    }
    resultTitle.textContent = preferences.title;
    resultSummary.innerHTML = `${preferences.days} ${preferences.days === 1 ? "session" : "sessions"} <span aria-hidden="true">/</span> ${goalLabels[preferences.goal]} <span aria-hidden="true">/</span> ${experienceLabels[preferences.experience]}`;
    customWorkouts.innerHTML = getSessions(preferences);
    resultPanel.hidden = false;
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message);
  } finally {
    isBusy = false;
    createButton.disabled = false;
    createButton.querySelector(".button-label").textContent = "Create my plan";
    loadingNotice.hidden = true;
  }
});