const workoutOptions = {
  strength: [
    [
      { title: "Full body A", exercises: ["Barbell squat", "Bench press", "Bent-over row", "Dead bug"] },
      { title: "Full body B", exercises: ["Deadlift", "Overhead press", "Lat pulldown", "Reverse lunge"] },
      { title: "Full body C", exercises: ["Front squat", "Incline dumbbell press", "Seated cable row", "Romanian deadlift"] }
    ],
    [
      { title: "Full body A", exercises: ["Trap-bar deadlift", "Dumbbell bench press", "Chest-supported row", "Step-up"] },
      { title: "Full body B", exercises: ["Leg press", "Push-up", "Single-arm row", "Hip thrust"] },
      { title: "Full body C", exercises: ["Goblet squat", "Landmine press", "Assisted pull-up", "Hamstring curl"] }
    ]
  ],
  muscle: [
    [
      { title: "Upper body A", exercises: ["Dumbbell bench press", "Lat pulldown", "Lateral raise", "Cable triceps press"] },
      { title: "Lower body", exercises: ["Leg press", "Romanian deadlift", "Leg curl", "Calf raise"] },
      { title: "Upper body B", exercises: ["Incline press", "Seated cable row", "Face pull", "Dumbbell curl"] }
    ],
    [
      { title: "Upper body A", exercises: ["Barbell bench press", "Assisted pull-up", "Cable fly", "Overhead triceps extension"] },
      { title: "Lower body", exercises: ["Goblet squat", "Hip thrust", "Split squat", "Seated calf raise"] },
      { title: "Upper body B", exercises: ["Shoulder press", "Chest-supported row", "Rear delt fly", "Hammer curl"] }
    ]
  ],
  fitness: [
    [
      { title: "Full body A", exercises: ["Goblet squat", "Dumbbell floor press", "Cable row", "Reverse lunge"] },
      { title: "Full body B", exercises: ["Step-up", "Incline push-up", "Romanian deadlift", "Mountain climber"] },
      { title: "Full body C", exercises: ["Leg press", "Dumbbell shoulder press", "Lat pulldown", "Bicycle crunch"] }
    ],
    [
      { title: "Full body A", exercises: ["Split squat", "Machine chest press", "Seated row", "Dead bug"] },
      { title: "Full body B", exercises: ["Hip hinge", "Knee push-up", "Dumbbell row", "Step-up"] },
      { title: "Full body C", exercises: ["Box squat", "Landmine press", "Assisted pull-up", "Plank shoulder tap"] }
    ]
  ]
};

const advancedWorkoutOptions = {
  strength: [
    { title: "Strength A", exercises: ["Trap-bar deadlift", "Barbell bench press", "Weighted pull-up", "Bulgarian split squat"] },
    { title: "Strength B", exercises: ["Front squat", "Overhead press", "Pendlay row", "Romanian deadlift"] },
    { title: "Strength C", exercises: ["Pause squat", "Incline bench press", "Barbell row", "Hip thrust"] }
  ],
  muscle: [
    { title: "Upper body A", exercises: ["Barbell bench press", "Weighted pull-up", "Cable fly", "Overhead triceps extension"] },
    { title: "Lower body", exercises: ["Front squat", "Barbell hip thrust", "Nordic hamstring curl", "Standing calf raise"] },
    { title: "Upper body B", exercises: ["Seated shoulder press", "T-bar row", "Rear delt fly", "Incline dumbbell curl"] }
  ],
  fitness: [
    { title: "Full body A", exercises: ["Front squat", "Dumbbell push press", "Renegade row", "Walking lunge"] },
    { title: "Full body B", exercises: ["Barbell deadlift", "Ring push-up", "Pull-up", "Hanging knee raise"] },
    { title: "Full body C", exercises: ["Reverse lunge", "Landmine press", "Single-leg RDL", "Plank shoulder tap"] }
  ]
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

const form = document.querySelector("#preferences-form");
const dayInput = document.querySelector("#days");
const workoutList = document.querySelector("#workout-list");
const planMessage = document.querySelector("#plan-message");
const planStatus = document.querySelector("#plan-status");
const planSummary = document.querySelector("#plan-summary");
const planTitle = document.querySelector("#plan-title");
const regenerateButton = document.querySelector("#regenerate-button");
const experienceTabs = Array.from(document.querySelectorAll(".experience-tab"));
const planCounts = { beginner: 1, intermediate: 0, advanced: 0 };
let selectedExperience = "beginner";
let isBusy = false;

function getPreferences() {
  const data = new FormData(form);
  const days = Number(data.get("days"));

  if (!Number.isInteger(days) || days < 1 || days > 7) {
    throw new Error("Choose between 1 and 7 workout days to build your plan.");
  }

  return {
    goal: data.get("goal"),
    days
  };
}

function getRepRange(goal, experience) {
  if (goal === "strength") {
    return experience === "advanced" ? "3-5" : experience === "intermediate" ? "4-6" : "6-8";
  }
  if (goal === "fitness") return "10-15";
  return experience === "advanced" ? "6-10" : "8-12";
}

function getSetCount(experience, goal) {
  if (experience === "advanced") return goal === "fitness" ? 3 : 4;
  if (experience === "beginner") return 2;
  return 3;
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function buildWorkoutMarkup(plan) {
  return plan.sessions.map((workout, index) => {
    const exerciseRows = workout.exercises.map((exercise) => `
      <tr>
        <td>${escapeHtml(exercise)}</td>
        <td>${plan.sets}</td>
        <td>${plan.reps}</td>
      </tr>`).join("");

    return `
      <article class="workout-card">
        <header class="workout-card-header">
          <div class="workout-card-title">
            <span class="workout-index">${String(index + 1).padStart(2, "0")}</span>
            <div class="workout-name"><strong>${escapeHtml(workout.title)}</strong><span>Session ${index + 1}</span></div>
          </div>
          <span class="workout-duration">4 exercises</span>
        </header>
        <table class="exercise-table">
          <thead><tr><th>Exercise</th><th>Sets</th><th>Reps</th></tr></thead>
          <tbody>${exerciseRows}</tbody>
        </table>
      </article>`;
  }).join("");
}

function createPlan(preferences, experience, variation) {
  const levelIndex = experience === "intermediate" ? 1 : 0;
  const workouts = experience === "advanced"
    ? advancedWorkoutOptions[preferences.goal]
    : workoutOptions[preferences.goal][(levelIndex + variation) % 2];
  return {
    goal: preferences.goal,
    experience,
    days: preferences.days,
    sets: getSetCount(experience, preferences.goal),
    reps: getRepRange(preferences.goal, experience),
    sessions: Array.from({ length: preferences.days }, (_, index) => workouts[(index + variation) % workouts.length])
  };
}

function updatePlan(plan) {
  workoutList.innerHTML = buildWorkoutMarkup(plan);
  workoutList.classList.remove("is-generating");
  planTitle.textContent = plan.days === 1 ? `Your ${experienceLabels[plan.experience].toLowerCase()} session` : `Your ${experienceLabels[plan.experience].toLowerCase()} plan`;
  planSummary.innerHTML = `${plan.days} ${plan.days === 1 ? "session" : "sessions"} <span aria-hidden="true">/</span> ${goalLabels[plan.goal]} <span aria-hidden="true">/</span> ${experienceLabels[plan.experience]}`;
  planStatus.className = "plan-status is-ready";
  planStatus.querySelector(".status-text").textContent = "Preview ready";
  planMessage.hidden = true;
}

function setBusy(busy) {
  isBusy = busy;
  regenerateButton.disabled = busy;
  experienceTabs.forEach((tab) => { tab.disabled = busy; });
  regenerateButton.innerHTML = busy ? "Building plan..." : '<span aria-hidden="true">&#8635;</span> Another plan';
  if (busy) {
    planStatus.className = "plan-status is-loading";
    planStatus.querySelector(".status-text").textContent = "Creating plan";
    planMessage.hidden = true;
    planTitle.textContent = `Building your ${experienceLabels[selectedExperience].toLowerCase()} plan`;
    workoutList.classList.add("is-generating");
  }
}

function showError(message) {
  planStatus.className = "plan-status is-error";
  planStatus.querySelector(".status-text").textContent = "Couldn't generate";
  planTitle.textContent = "Let's try that again";
  planMessage.innerHTML = `<span class="message-icon" aria-hidden="true">!</span><span>${escapeHtml(message)}</span>`;
  planMessage.hidden = false;
  workoutList.classList.remove("is-generating");
}

async function generatePlan() {
  if (isBusy) return;

  let preferences;
  try {
    preferences = getPreferences();
  } catch (error) {
    showError(error.message);
    dayInput.focus();
    return;
  }

  setBusy(true);
  await new Promise((resolve) => window.setTimeout(resolve, 850));

  try {
    if (new URLSearchParams(window.location.search).has("simulateError")) {
      throw new Error("The plan service is taking a break. Please try again in a moment.");
    }
    const plan = createPlan(preferences, selectedExperience, planCounts[selectedExperience]);
    planCounts[selectedExperience] += 1;
    updatePlan(plan);
  } catch (error) {
    showError(error.message || "Something went wrong while building your plan. Please try again.");
  } finally {
    setBusy(false);
  }
}

experienceTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    selectedExperience = tab.dataset.experience;
    experienceTabs.forEach((item) => {
      const isSelected = item === tab;
      item.classList.toggle("is-active", isSelected);
      item.setAttribute("aria-selected", String(isSelected));
      item.tabIndex = isSelected ? 0 : -1;
    });
    generatePlan();
  });
});

form.addEventListener("change", (event) => {
  if (event.target.name === "goal" || event.target.id === "days") generatePlan();
});

regenerateButton.addEventListener("click", generatePlan);

document.querySelectorAll(".stepper-button").forEach((button) => {
  button.addEventListener("click", () => {
    const nextValue = Math.min(7, Math.max(1, Number(dayInput.value || 1) + Number(button.dataset.step)));
    dayInput.value = String(nextValue);
    dayInput.dispatchEvent(new Event("change", { bubbles: true }));
  });
});

dayInput.addEventListener("change", () => {
  const value = Number(dayInput.value);
  if (Number.isInteger(value)) dayInput.value = String(Math.min(7, Math.max(1, value)));
});

updatePlan(createPlan({ goal: "muscle", days: 3 }, selectedExperience, 0));