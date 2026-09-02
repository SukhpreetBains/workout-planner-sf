trigger AccountTrigger on Account__c (before insert) { new AccountService().touch(); }
