import { LightningElement, api, wire } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
import { getObjectInfo, getPicklistValues } from 'lightning/uiObjectInfoApi';
import WORKOUT_PLAN_OBJECT from '@salesforce/schema/Workout_Plan__c';
import GOAL_FIELD from '@salesforce/schema/Workout_Plan__c.Goal__c';
import createPlan from '@salesforce/apex/WorkoutPlanController.createPlan';
import getPlan from '@salesforce/apex/WorkoutPlanController.getPlan';

const POLL_INTERVAL_MS = 1500;
const MAX_POLL_ATTEMPTS = 40;

export default class WorkoutPlanner extends NavigationMixin(LightningElement) {
    @api experienceCloudMode = false;
    goal = 'Muscle';
    daysPerWeek = 3;
    activeExperience = 'Beginner';
    goalOptions = [];
    plansByExperience = {};
    isCustomPlanOpen = false;
    errorMessage = '';
    errorExperience = '';
    loadingExperience = '';

    @wire(getObjectInfo, { objectApiName: WORKOUT_PLAN_OBJECT })
    objectInfo;

    @wire(getPicklistValues, {
        recordTypeId: '$objectInfo.data.defaultRecordTypeId',
        fieldApiName: GOAL_FIELD
    })
    wiredGoalOptions({ data, error }) {
        if (data) {
            this.goalOptions = data.values.map(({ label, value }) => ({ label, value }));
        } else if (error) {
            this.setError(error);
        }
    }

    get isLoading() { return Boolean(this.loadingExperience); }
    get beginnerPlan() { return this.plansByExperience.Beginner; }
    get intermediatePlan() { return this.plansByExperience.Intermediate; }
    get advancedPlan() { return this.plansByExperience.Advanced; }
    get beginnerHasPlan() { return Boolean(this.beginnerPlan); }
    get intermediateHasPlan() { return Boolean(this.intermediatePlan); }
    get advancedHasPlan() { return Boolean(this.advancedPlan); }
    get beginnerIsLoading() { return this.loadingExperience === 'Beginner'; }
    get intermediateIsLoading() { return this.loadingExperience === 'Intermediate'; }
    get advancedIsLoading() { return this.loadingExperience === 'Advanced'; }
    get beginnerHasError() { return this.errorExperience === 'Beginner' && Boolean(this.errorMessage); }
    get intermediateHasError() { return this.errorExperience === 'Intermediate' && Boolean(this.errorMessage); }
    get advancedHasError() { return this.errorExperience === 'Advanced' && Boolean(this.errorMessage); }
    get beginnerNeedsPlan() { return !this.beginnerIsLoading && !this.beginnerHasPlan && !this.beginnerHasError; }
    get intermediateNeedsPlan() { return !this.intermediateIsLoading && !this.intermediateHasPlan && !this.intermediateHasError; }
    get advancedNeedsPlan() { return !this.advancedIsLoading && !this.advancedHasPlan && !this.advancedHasError; }
    get beginnerButtonLabel() { return this.beginnerHasPlan ? 'Another beginner plan' : 'Generate beginner plan'; }
    get intermediateButtonLabel() { return this.intermediateHasPlan ? 'Another intermediate plan' : 'Generate intermediate plan'; }
    get advancedButtonLabel() { return this.advancedHasPlan ? 'Another advanced plan' : 'Generate advanced plan'; }
    handleGoalChange(event) {
        this.goal = event.detail.value;
        this.plansByExperience = {};
        this.errorMessage = '';
        this.errorExperience = '';
    }

    handleExperienceTab(event) {
        const experience = event.currentTarget.value;
        this.activeExperience = experience;
        this.errorMessage = '';
        this.errorExperience = '';
        if (!this.plansByExperience[experience]) {
            this.generatePlanFor(experience);
        }
    }

    handleDaysChange(event) {
        this.daysPerWeek = event.detail.value;
        this.plansByExperience = {};
        this.errorMessage = '';
        this.errorExperience = '';
    }

    handleRegenerate(event) {
        this.generatePlanFor(event.currentTarget.dataset.experience);
    }

    handleCreateCustomPlan() {
        if (this.experienceCloudMode) {
            this.isCustomPlanOpen = true;
            return;
        }
        this[NavigationMixin.Navigate]({
            type: 'standard__navItemPage',
            attributes: { apiName: 'Workout_Planner_Custom_Plan' }
        });
    }

    handleCustomPlanBack() {
        this.isCustomPlanOpen = false;
    }

    async generatePlanFor(experience) {
        if (this.isLoading || !this.goalOptions.length) return;
        const dayCount = Number(this.daysPerWeek);
        if (!Number.isInteger(dayCount) || dayCount < 1 || dayCount > 7) {
            this.errorMessage = 'Choose between 1 and 7 workout days to build your plan.';
            this.errorExperience = experience;
            return;
        }

        this.loadingExperience = experience;
        this.errorMessage = '';
        this.errorExperience = '';
        try {
            const planId = await createPlan({
                goal: this.goal,
                experience,
                daysPerWeek: dayCount,
                equipmentPreference: 'Full_Gym',
                planTitle: '',
                additionalNotes: ''
            });
            const plan = await this.waitForPlan(planId);
            this.plansByExperience = { ...this.plansByExperience, [experience]: plan };
        } catch (error) {
            this.setError(error, experience);
        } finally {
            this.loadingExperience = '';
        }
    }

    async waitForPlan(planId) {
        for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
            const plan = await getPlan({ planId });
            if (plan.status === 'Ready') return plan;
            if (plan.status === 'Failed') {
                throw new Error('We could not generate your plan. Please try again in a moment.');
            }
            await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
        }
        throw new Error('Your plan is taking longer than expected. Please try again.');
    }

    setError(error, experience) {
        const message = error && error.body && error.body.message
            ? error.body.message
            : error && error.message;
        this.errorMessage = message || 'Something went wrong while building your plan. Please try again.';
        this.errorExperience = experience || this.activeExperience;
    }
}