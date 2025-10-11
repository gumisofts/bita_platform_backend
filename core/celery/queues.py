from kombu import Queue


class CeleryQueue:
    class Definitions:
        # HIGHEST PRIORITY - Critical business operations
        PAYMENT_PROCESSING = "payment-processing"           # Priority 1
        ORDER_FULFILLMENT = "order-fulfillment"             # Priority 1
        INVENTORY_ALERTS = "inventory-alerts"               # Priority 1
        
        # HIGH PRIORITY - User-facing features
        REAL_TIME_NOTIFICATIONS = "real-time-notifications" # Priority 2
        CHAT_MESSAGING = "chat-messaging"                   # Priority 2
        USER_VERIFICATION = "user-verification"             # Priority 2
        
        # MEDIUM PRIORITY - Business operations
        FINANCIAL_REPORTING = "financial-reporting"         # Priority 3
        INVENTORY_SYNC = "inventory-sync"                   # Priority 3
        CRM_OPERATIONS = "crm-operations"                    # Priority 3
        
        # LOW PRIORITY - Background tasks
        FILE_PROCESSING = "file-processing"                 # Priority 4
        EMAIL_NOTIFICATIONS = "email-notifications"         # Priority 4
        ANALYTICS_PROCESSING = "analytics-processing"       # Priority 4
        
        # LOWEST PRIORITY - System maintenance
        LOGGING = "logging"                                  # Priority 5
        SYSTEM_MAINTENANCE = "system-maintenance"           # Priority 5
        BEATS = "beats"                                      # Priority 5
        

    @staticmethod
    def queues():
        return tuple(
            (Queue(getattr(CeleryQueue.Definitions, item)))
            for item in filter(
                lambda ref: not ref.startswith("_"), dir(CeleryQueue.Definitions)
            )
        )
    
    @staticmethod
    def get_queue_priority(queue_name):
        """Return priority level for queue routing"""
        priority_map = {
            # Priority 1 - Critical
            'payment-processing': 1,
            'order-fulfillment': 1,
            'inventory-alerts': 1,
            
            # Priority 2 - High
            'real-time-notifications': 2,
            'chat-messaging': 2,
            'user-verification': 2,
            
            # Priority 3 - Medium
            'financial-reporting': 3,
            'inventory-sync': 3,
            'crm-operations': 3,
            
            # Priority 4 - Low
            'file-processing': 4,
            'email-notifications': 4,
            'analytics-processing': 4,
            
            # Priority 5 - Lowest
            'logging': 5,
            'system-maintenance': 5,
            'beats': 5,
        }
        return priority_map.get(queue_name, 5)
