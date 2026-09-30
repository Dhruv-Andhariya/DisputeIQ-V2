export const ROLES = ['ADMIN', 'INVESTIGATOR', 'ANALYST', 'VIEWER'];

export const ROLE_DESCRIPTIONS = {
  ADMIN: 'Manages the organization and users, investigates, and makes final review decisions.',
  INVESTIGATOR: 'Views cases and runs investigations.',
  ANALYST: 'Views cases, evidence, and investigation results.',
  VIEWER: 'Read-only access to cases.',
};

export const PERMISSION_LABELS = {
  'cases:view': 'View cases, evidence & results',
  'cases:investigate': 'Run investigations',
  'cases:review': 'Approve / reject disputes',
  'users:manage': 'Manage users',
  'organization:manage': 'Manage organization',
  'organization:audit': 'View organization activity',
};
