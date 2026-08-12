trigger BillingTrigger on Billing__c (after insert, after update) {
    new BillingHandler().run();
}
