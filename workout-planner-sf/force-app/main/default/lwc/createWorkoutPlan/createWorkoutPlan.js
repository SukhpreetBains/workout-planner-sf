import { LightningElement, api, wire } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
import { getObjectInfo, getPicklistValues } from 'lightning/uiObjectInfoApi';
import WORKOUT_PLAN_OBJECT from '@salesforce/schema/Workout_Plan__c';
import GOAL_FIELD from '@salesforce/schema/Workout_Plan__c.Goal__c';
import EXPERIENCE_FIELD from '@salesforce/schema/Workout_Plan__c.Experience_Level__c';
import EQUIPMENT_FIELD from '@salesforce/schema/Workout_Plan__c.Equipment_Preference__c';
import createPlan from '@salesforce/apex/WorkoutPlanController.createPlan';
import getPlan from '@salesforce/apex/WorkoutPlanController.getPlan';

const POLL_INTERVAL_MS = 1500;
const MAX_POLL_ATTEMPTS = 40;

export default class CreateWorkoutPlan extends NavigationMixin(LightningElement) {
    @api experienceCloudMode = false;
    @api inPlaceMode = false;
    planTitle = 'My workout plan';
    goal = 'Muscle';
    experience = 'Beginner';
    equipmentPreference = 'Full_Gym';
    daysPerWeek = 3;
    additionalNotes = '';
    goalOptions = [];
    experienceOptions = [];
    equipmentOptions = [];
    plan;
    errorMessage = '';
    isLoading = false;

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

    @wire(getPicklistValues, {
        recordTypeId: '$objectInfo.data.defaultRecordTypeId',
        fieldApiName: EXPERIENCE_FIELD
    })
    wiredExperienceOptions({ data, error }) {
        if (data) {
            this.experienceOptions = data.values.map(({ label, value }) => ({ label, value }));
        } else if (error) {
            this.setError(error);
        }
    }

    @wire(getPicklistValues, {
        recordTypeId: '$objectInfo.data.defaultRecordTypeId',
        fieldApiName: EQUIPMENT_FIELD
    })
    wiredEquipmentOptions({ data, error }) {
        if (data) {
            this.equipmentOptions = data.values.map(({ label, value }) => ({ label, value }));
        } else if (error) {
            this.setError(error);
        }
    }

    get isSubmitDisabled() {
        return this.isLoading || !this.goalOptions.length || !this.experienceOptions.length || !this.equipmentOptions.length;
    }

    get submitLabel() {
        return this.isLoading ? 'Generating...' : 'Create plan';
    }

    get hasPlan() {
        return Boolean(this.plan && this.plan.status === 'Ready');
    }

    get hasError() {
        return Boolean(this.errorMessage);
    }

    handlePlanTitleChange(event) { this.planTitle = event.detail.value; }
    handleGoalChange(event) { this.goal = event.detail.value; }
    handleExperienceChange(event) { this.experience = event.detail.value; }
    handleEquipmentChange(event) { this.equipmentPreference = event.detail.value; }
    handleDaysChange(event) { this.daysPerWeek = event.detail.value; }
    handleNotesChange(event) { this.additionalNotes = event.detail.value; }

    async handleCreate() {
        if (this.isLoading || !this.validateInputs()) return;
        this.isLoading = true;
        this.errorMessage = '';
        this.plan = undefined;
        try {
            const planId = await createPlan({
                goal: this.goal,
                experience: this.experience,
                daysPerWeek: Number(this.daysPerWeek),
                equipmentPreference: this.equipmentPreference,
                planTitle: this.planTitle,
                additionalNotes: this.additionalNotes
            });
            this.plan = await this.waitForPlan(planId);
        } catch (error) {
            this.setError(error);
        } finally {
            this.isLoading = false;
        }
    }

    validateInputs() {
        const inputs = this.template.querySelectorAll('lightning-input, lightning-combobox, lightning-textarea');
        let isValid = true;
        inputs.forEach((input) => {
            if (!input.reportValidity()) isValid = false;
        });
        const dayCount = Number(this.daysPerWeek);
        if (!Number.isInteger(dayCount) || dayCount < 1 || dayCount > 7) {
            this.errorMessage = 'Choose between 1 and 7 workout days.';
            return false;
        }
        return isValid;
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

    handleBack() {
        if (this.inPlaceMode) {
            this.dispatchEvent(new CustomEvent('back'));
            return;
        }
        const pageReference = this.experienceCloudMode
            ? { type: 'comm__namedPage', attributes: { name: 'Home' } }
            : { type: 'standard__navItemPage', attributes: { apiName: 'Workout_Planner' } };
        this[NavigationMixin.Navigate](pageReference);
    }

    setError(error) {
        const message = error && error.body && error.body.message
            ? error.body.message
            : error && error.message;
        this.errorMessage = message || 'Something went wrong while building your plan. Please try again.';
    }
}