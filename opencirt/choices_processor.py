def choices_context(request):
    return {
        # Incident related choices
        'INCIDENT_STATUS_CHOICES': [
            ('OPEN', 'Open'),
            ('IN_PROGRESS', 'In Progress'),
            ('RESOLVED', 'Resolved'),
            ('CLOSED', 'Closed'),
        ],
        'INCIDENT_SEVERITY_CHOICES': [
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ],

        # User roles choices
        'USER_ROLES_CHOICES': [
            ('INCIDENT_LEAD', 'Incident Lead'),
            ('RESPONDER', 'Responder'),
            ('READER', 'Reader'),
        ],

        # IOC (Indicator of Compromise) related choices
        'GENERIC_IOC_STATUS_CHOICES': [
            ('COMPROMISED', 'Compromised'),
            ('POTENTIALLY_COMPROMISED', 'Potentially Compromised'),
            ('SAFE', 'Safe'),
        ],
        'IP_TYPE_CHOICES': [
            ('PRIVATE', 'Private'),
            ('PUBLIC', 'Public'),
            ('PUBLIC_OWNED', 'Public Owned'),
        ], 
        'GENERIC_IOC_TYPE_CHOICES': [
            ('IPADRESS', 'IP Address'),
            ('URL', 'URL'),
            ('DOMAIN', 'Domain'),
            ('NETWORK', 'Network / CIDR'),
            ('EMAIL', 'Email'),
            ('HASH', 'Hash'),
            ('FILE', 'File'),
            ('FILENAME', 'Filename'),
            ('ACCOUNT', 'Account'),
            ('PASSWORD', 'Password'),
            ('FOLDER', 'Folder'),
            ('SRC_PORT', 'Source Port'),
            ('DST_PORT', 'Destination Port'),
            ('DEVICE', 'Device'),
            ('ISP', 'Isp'),
            ('PERSON', 'Person'),
            ('OTHER', 'Other'),
        ],

        # Action related choices
        'GENERIC_ACTION_CHOICES': [
            ('MALICIOUS', 'Malicious'),
            ('DEFENSIVE', 'Defensive'),
            ('MITIGATION', 'Mitigation'),
            ('COMMUNICATION', 'Communication'),
            ('ALERT', 'Alert'),
            ('OTHER', 'Other'),
        ],

        # Task related choices
        'TASK_STATUS_CHOICES': [
            ('OPEN', 'Open'),
            ('IN_PROGRESS', 'In Progress'),
            ('DONE', 'Done'),
        ],
        'TASK_PRIORITY_CHOICES': [
            ('URGENT', 'Urgent'),
            ('HIGH', 'High'),
            ('MEDIUM', 'Medium'),
            ('LOW', 'Low'),
        ],

        # Impact related choices
        'IMPACT_TYPES_CHOICES': [
            ('BUSINESS_IMPACT', 'Business impact'),
            ('REPUTATION', 'Reputation'),
            ('DATA_LOSS', 'Data Loss'),
            ('SYSTEMS_AVAILABILITY', 'Systems availability'),
            ('NOT_DEFINED', 'Not defined'),
        ],
        'IMPACT_SEVERITY_CHOICES': [
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ],
        'IMPACT_STATUS_CHOICES': [
            ('CONTINUOUS', 'Continuous'),
            ('IN_PROGRESS', 'In Progress'),
            ('RESOLVED', 'Resolved'),
            ('CLOSED', 'Closed'),
        ],
    }
