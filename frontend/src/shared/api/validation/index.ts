/** Runtime guards for API payloads, grouped by domain. */
export { isRecord, validate } from './core';
export type { Validator } from './core';
export {
  isAuthResponse,
  isAuthStatus,
  isCreatedCustomer,
  isCustomerAccount,
  isCustomerAccountList,
  isUser,
} from './accounts';
export { isCompanyIdentity, isConfig, isHealth } from './workspace';
export { isDocumentDetail, isDocumentList, isUploadResult } from './documents';
export { isToolList, isToolTrace } from './tools';
export { isChatResponse, isConversationList } from './chat';
export { isRequestList } from './requests';
