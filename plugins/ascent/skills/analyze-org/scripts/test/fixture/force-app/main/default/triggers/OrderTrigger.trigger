trigger OrderTrigger on Order__c (after insert) { new OrderService().calc(); }
