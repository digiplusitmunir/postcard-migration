import type { Schema, Attribute } from '@strapi/strapi';

export interface AdminPermission extends Schema.CollectionType {
  collectionName: 'admin_permissions';
  info: {
    name: 'Permission';
    description: '';
    singularName: 'permission';
    pluralName: 'permissions';
    displayName: 'Permission';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    action: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    actionParameters: Attribute.JSON & Attribute.DefaultTo<{}>;
    subject: Attribute.String &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    properties: Attribute.JSON & Attribute.DefaultTo<{}>;
    conditions: Attribute.JSON & Attribute.DefaultTo<[]>;
    role: Attribute.Relation<'admin::permission', 'manyToOne', 'admin::role'>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'admin::permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'admin::permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface AdminUser extends Schema.CollectionType {
  collectionName: 'admin_users';
  info: {
    name: 'User';
    description: '';
    singularName: 'user';
    pluralName: 'users';
    displayName: 'User';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    firstname: Attribute.String &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    lastname: Attribute.String &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    username: Attribute.String;
    email: Attribute.Email &
      Attribute.Required &
      Attribute.Private &
      Attribute.Unique &
      Attribute.SetMinMaxLength<{
        minLength: 6;
      }>;
    password: Attribute.Password &
      Attribute.Private &
      Attribute.SetMinMaxLength<{
        minLength: 6;
      }>;
    resetPasswordToken: Attribute.String & Attribute.Private;
    registrationToken: Attribute.String & Attribute.Private;
    isActive: Attribute.Boolean &
      Attribute.Private &
      Attribute.DefaultTo<false>;
    roles: Attribute.Relation<'admin::user', 'manyToMany', 'admin::role'> &
      Attribute.Private;
    blocked: Attribute.Boolean & Attribute.Private & Attribute.DefaultTo<false>;
    preferedLanguage: Attribute.String;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<'admin::user', 'oneToOne', 'admin::user'> &
      Attribute.Private;
    updatedBy: Attribute.Relation<'admin::user', 'oneToOne', 'admin::user'> &
      Attribute.Private;
  };
}

export interface AdminRole extends Schema.CollectionType {
  collectionName: 'admin_roles';
  info: {
    name: 'Role';
    description: '';
    singularName: 'role';
    pluralName: 'roles';
    displayName: 'Role';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    name: Attribute.String &
      Attribute.Required &
      Attribute.Unique &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    code: Attribute.String &
      Attribute.Required &
      Attribute.Unique &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    description: Attribute.String;
    users: Attribute.Relation<'admin::role', 'manyToMany', 'admin::user'>;
    permissions: Attribute.Relation<
      'admin::role',
      'oneToMany',
      'admin::permission'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<'admin::role', 'oneToOne', 'admin::user'> &
      Attribute.Private;
    updatedBy: Attribute.Relation<'admin::role', 'oneToOne', 'admin::user'> &
      Attribute.Private;
  };
}

export interface AdminApiToken extends Schema.CollectionType {
  collectionName: 'strapi_api_tokens';
  info: {
    name: 'Api Token';
    singularName: 'api-token';
    pluralName: 'api-tokens';
    displayName: 'Api Token';
    description: '';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    name: Attribute.String &
      Attribute.Required &
      Attribute.Unique &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    description: Attribute.String &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }> &
      Attribute.DefaultTo<''>;
    type: Attribute.Enumeration<['read-only', 'full-access', 'custom']> &
      Attribute.Required &
      Attribute.DefaultTo<'read-only'>;
    accessKey: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    lastUsedAt: Attribute.DateTime;
    permissions: Attribute.Relation<
      'admin::api-token',
      'oneToMany',
      'admin::api-token-permission'
    >;
    expiresAt: Attribute.DateTime;
    lifespan: Attribute.BigInteger;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'admin::api-token',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'admin::api-token',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface AdminApiTokenPermission extends Schema.CollectionType {
  collectionName: 'strapi_api_token_permissions';
  info: {
    name: 'API Token Permission';
    description: '';
    singularName: 'api-token-permission';
    pluralName: 'api-token-permissions';
    displayName: 'API Token Permission';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    action: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    token: Attribute.Relation<
      'admin::api-token-permission',
      'manyToOne',
      'admin::api-token'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'admin::api-token-permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'admin::api-token-permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface AdminTransferToken extends Schema.CollectionType {
  collectionName: 'strapi_transfer_tokens';
  info: {
    name: 'Transfer Token';
    singularName: 'transfer-token';
    pluralName: 'transfer-tokens';
    displayName: 'Transfer Token';
    description: '';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    name: Attribute.String &
      Attribute.Required &
      Attribute.Unique &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    description: Attribute.String &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }> &
      Attribute.DefaultTo<''>;
    accessKey: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    lastUsedAt: Attribute.DateTime;
    permissions: Attribute.Relation<
      'admin::transfer-token',
      'oneToMany',
      'admin::transfer-token-permission'
    >;
    expiresAt: Attribute.DateTime;
    lifespan: Attribute.BigInteger;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'admin::transfer-token',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'admin::transfer-token',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface AdminTransferTokenPermission extends Schema.CollectionType {
  collectionName: 'strapi_transfer_token_permissions';
  info: {
    name: 'Transfer Token Permission';
    description: '';
    singularName: 'transfer-token-permission';
    pluralName: 'transfer-token-permissions';
    displayName: 'Transfer Token Permission';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    action: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        minLength: 1;
      }>;
    token: Attribute.Relation<
      'admin::transfer-token-permission',
      'manyToOne',
      'admin::transfer-token'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'admin::transfer-token-permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'admin::transfer-token-permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginUploadFile extends Schema.CollectionType {
  collectionName: 'files';
  info: {
    singularName: 'file';
    pluralName: 'files';
    displayName: 'File';
    description: '';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    name: Attribute.String & Attribute.Required;
    alternativeText: Attribute.String;
    caption: Attribute.String;
    width: Attribute.Integer;
    height: Attribute.Integer;
    formats: Attribute.JSON;
    hash: Attribute.String & Attribute.Required;
    ext: Attribute.String;
    mime: Attribute.String & Attribute.Required;
    size: Attribute.Decimal & Attribute.Required;
    url: Attribute.String & Attribute.Required;
    previewUrl: Attribute.String;
    provider: Attribute.String & Attribute.Required;
    provider_metadata: Attribute.JSON;
    related: Attribute.Relation<'plugin::upload.file', 'morphToMany'>;
    folder: Attribute.Relation<
      'plugin::upload.file',
      'manyToOne',
      'plugin::upload.folder'
    > &
      Attribute.Private;
    folderPath: Attribute.String &
      Attribute.Required &
      Attribute.Private &
      Attribute.SetMinMax<{
        min: 1;
      }>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::upload.file',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::upload.file',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginUploadFolder extends Schema.CollectionType {
  collectionName: 'upload_folders';
  info: {
    singularName: 'folder';
    pluralName: 'folders';
    displayName: 'Folder';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    name: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMax<{
        min: 1;
      }>;
    pathId: Attribute.Integer & Attribute.Required & Attribute.Unique;
    parent: Attribute.Relation<
      'plugin::upload.folder',
      'manyToOne',
      'plugin::upload.folder'
    >;
    children: Attribute.Relation<
      'plugin::upload.folder',
      'oneToMany',
      'plugin::upload.folder'
    >;
    files: Attribute.Relation<
      'plugin::upload.folder',
      'oneToMany',
      'plugin::upload.file'
    >;
    path: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMax<{
        min: 1;
      }>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::upload.folder',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::upload.folder',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginUsersPermissionsPermission
  extends Schema.CollectionType {
  collectionName: 'up_permissions';
  info: {
    name: 'permission';
    description: '';
    singularName: 'permission';
    pluralName: 'permissions';
    displayName: 'Permission';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    action: Attribute.String & Attribute.Required;
    role: Attribute.Relation<
      'plugin::users-permissions.permission',
      'manyToOne',
      'plugin::users-permissions.role'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::users-permissions.permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::users-permissions.permission',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginUsersPermissionsRole extends Schema.CollectionType {
  collectionName: 'up_roles';
  info: {
    name: 'role';
    description: '';
    singularName: 'role';
    pluralName: 'roles';
    displayName: 'Role';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    name: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        minLength: 3;
      }>;
    description: Attribute.String;
    type: Attribute.String & Attribute.Unique;
    permissions: Attribute.Relation<
      'plugin::users-permissions.role',
      'oneToMany',
      'plugin::users-permissions.permission'
    >;
    users: Attribute.Relation<
      'plugin::users-permissions.role',
      'oneToMany',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::users-permissions.role',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::users-permissions.role',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginUsersPermissionsUser extends Schema.CollectionType {
  collectionName: 'up_users';
  info: {
    name: 'user';
    description: '';
    singularName: 'user';
    pluralName: 'users';
    displayName: 'User';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    username: Attribute.String &
      Attribute.Required &
      Attribute.Unique &
      Attribute.SetMinMaxLength<{
        minLength: 3;
      }>;
    email: Attribute.Email &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        minLength: 6;
      }>;
    provider: Attribute.String;
    password: Attribute.Password &
      Attribute.Private &
      Attribute.SetMinMaxLength<{
        minLength: 6;
      }>;
    resetPasswordToken: Attribute.String & Attribute.Private;
    confirmationToken: Attribute.String & Attribute.Private;
    confirmed: Attribute.Boolean & Attribute.DefaultTo<false>;
    blocked: Attribute.Boolean & Attribute.DefaultTo<false>;
    role: Attribute.Relation<
      'plugin::users-permissions.user',
      'manyToOne',
      'plugin::users-permissions.role'
    >;
    user_type: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToOne',
      'api::user-type.user-type'
    >;
    fullName: Attribute.String;
    slug: Attribute.UID<'plugin::users-permissions.user', 'fullName'>;
    profilePic: Attribute.Media;
    coverImage: Attribute.Media;
    isFeatured: Attribute.Boolean & Attribute.DefaultTo<false>;
    priority: Attribute.Integer & Attribute.DefaultTo<100>;
    bio: Attribute.RichText;
    social: Attribute.Component<'social.social'>;
    isInstaActive: Attribute.Boolean;
    postcards: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::postcard.postcard'
    >;
    albums: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::album.album'
    >;
    seo: Attribute.Component<'shared.seo'>;
    profilePicURL: Attribute.String;
    fbId: Attribute.String;
    tracking: Attribute.Component<'tracking.tracking'>;
    company: Attribute.Relation<
      'plugin::users-permissions.user',
      'manyToOne',
      'api::company.company'
    >;
    country: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToOne',
      'api::country.country'
    >;
    bookmarks: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::bookmark.bookmark'
    >;
    chats: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::chat.chat'
    >;
    follows: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::follow.follow'
    >;
    followings: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::follow.follow'
    >;
    profile: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToOne',
      'api::profile.profile'
    >;
    city: Attribute.String;
    firstName: Attribute.String;
    lastName: Attribute.String;
    follow_albums: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::follow-album.follow-album'
    >;
    follow_companies: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::follow-company.follow-company'
    >;
    follow_affiliates: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::follow-affiliate.follow-affiliate'
    >;
    isLoyaltyMember: Attribute.Boolean & Attribute.DefaultTo<false>;
    destination_expert: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToOne',
      'api::destination-expert.destination-expert'
    >;
    follow_tags: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::follow-tag.follow-tag'
    >;
    dx_cards: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::dx-card.dx-card'
    >;
    travelogues: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::travelogue.travelogue'
    >;
    restaurants: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::restaurant.restaurant'
    >;
    memories: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::memory.memory'
    >;
    memory: Attribute.Relation<
      'plugin::users-permissions.user',
      'manyToOne',
      'api::memory.memory'
    >;
    follow_city_guides: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::follow-city-guide.follow-city-guide'
    >;
    property_itineraries: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToMany',
      'api::property-itinerary.property-itinerary'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::users-permissions.user',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginEmailDesignerEmailTemplate
  extends Schema.CollectionType {
  collectionName: 'email_templates';
  info: {
    singularName: 'email-template';
    pluralName: 'email-templates';
    displayName: 'Email-template';
    name: 'email-template';
  };
  options: {
    draftAndPublish: false;
    timestamps: true;
    increments: true;
    comment: '';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    templateReferenceId: Attribute.Integer & Attribute.Unique;
    design: Attribute.JSON;
    name: Attribute.String;
    subject: Attribute.String;
    bodyHtml: Attribute.Text;
    bodyText: Attribute.Text;
    enabled: Attribute.Boolean & Attribute.DefaultTo<true>;
    tags: Attribute.JSON;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::email-designer.email-template',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::email-designer.email-template',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginWebsiteBuilderLog extends Schema.CollectionType {
  collectionName: 'logs';
  info: {
    singularName: 'log';
    pluralName: 'logs';
    displayName: 'logs';
  };
  options: {
    draftAndPublish: false;
    comment: '';
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    status: Attribute.Integer;
    trigger: Attribute.Enumeration<['manual', 'cron', 'event']> &
      Attribute.DefaultTo<'manual'>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::website-builder.log',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::website-builder.log',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginChartbrewChartbrew extends Schema.SingleType {
  collectionName: 'chartbrews';
  info: {
    singularName: 'chartbrew';
    pluralName: 'chartbrews';
    displayName: 'Chartbrew';
  };
  options: {
    draftAndPublish: false;
    comment: '';
  };
  attributes: {
    host: Attribute.String & Attribute.Required;
    token: Attribute.String & Attribute.Required;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::chartbrew.chartbrew',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::chartbrew.chartbrew',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginI18NLocale extends Schema.CollectionType {
  collectionName: 'i18n_locale';
  info: {
    singularName: 'locale';
    pluralName: 'locales';
    collectionName: 'locales';
    displayName: 'Locale';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    name: Attribute.String &
      Attribute.SetMinMax<{
        min: 1;
        max: 50;
      }>;
    code: Attribute.String & Attribute.Unique;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::i18n.locale',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::i18n.locale',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginCommentsComment extends Schema.CollectionType {
  collectionName: 'comments_comment';
  info: {
    tableName: 'plugin-comments-comments';
    singularName: 'comment';
    pluralName: 'comments';
    displayName: 'Comment';
    description: 'Comment content type';
    kind: 'collectionType';
  };
  options: {
    draftAndPublish: false;
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    content: Attribute.Text & Attribute.Required;
    blocked: Attribute.Boolean & Attribute.DefaultTo<false>;
    blockedThread: Attribute.Boolean & Attribute.DefaultTo<false>;
    blockReason: Attribute.String;
    authorUser: Attribute.Relation<
      'plugin::comments.comment',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    authorId: Attribute.String;
    authorName: Attribute.String;
    authorEmail: Attribute.Email;
    authorAvatar: Attribute.String;
    isAdminComment: Attribute.Boolean;
    removed: Attribute.Boolean;
    approvalStatus: Attribute.String;
    related: Attribute.String;
    reports: Attribute.Relation<
      'plugin::comments.comment',
      'oneToMany',
      'plugin::comments.comment-report'
    >;
    threadOf: Attribute.Relation<
      'plugin::comments.comment',
      'oneToOne',
      'plugin::comments.comment'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::comments.comment',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::comments.comment',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface PluginCommentsCommentReport extends Schema.CollectionType {
  collectionName: 'comments_comment-report';
  info: {
    tableName: 'plugin-comments-reports';
    singularName: 'comment-report';
    pluralName: 'comment-reports';
    displayName: 'Reports';
    description: 'Reports content type';
    kind: 'collectionType';
  };
  options: {
    draftAndPublish: false;
  };
  pluginOptions: {
    'content-manager': {
      visible: false;
    };
    'content-type-builder': {
      visible: false;
    };
  };
  attributes: {
    content: Attribute.Text;
    reason: Attribute.Enumeration<['BAD_LANGUAGE', 'DISCRIMINATION', 'OTHER']> &
      Attribute.Required &
      Attribute.DefaultTo<'OTHER'>;
    resolved: Attribute.Boolean & Attribute.DefaultTo<false>;
    related: Attribute.Relation<
      'plugin::comments.comment-report',
      'manyToOne',
      'plugin::comments.comment'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'plugin::comments.comment-report',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'plugin::comments.comment-report',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiAboutUsProfileAboutUsProfile extends Schema.CollectionType {
  collectionName: 'about_us_profiles';
  info: {
    singularName: 'about-us-profile';
    pluralName: 'about-us-profiles';
    displayName: 'AboutUsProfile';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    frontImage: Attribute.Media;
    backImage: Attribute.Media;
    link: Attribute.String;
    priority: Attribute.Integer & Attribute.DefaultTo<100>;
    about_us_section: Attribute.Relation<
      'api::about-us-profile.about-us-profile',
      'manyToOne',
      'api::about-us-section.about-us-section'
    >;
    company: Attribute.Relation<
      'api::about-us-profile.about-us-profile',
      'oneToOne',
      'api::company.company'
    >;
    designation: Attribute.Enumeration<
      ['Founder', 'CEO', 'Manager', 'Administrator']
    > &
      Attribute.DefaultTo<'Founder'>;
    country: Attribute.Relation<
      'api::about-us-profile.about-us-profile',
      'oneToOne',
      'api::country.country'
    >;
    subTitle: Attribute.Text;
    about: Attribute.Text;
    postcardRole: Attribute.String;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::about-us-profile.about-us-profile',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::about-us-profile.about-us-profile',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiAboutUsSectionAboutUsSection extends Schema.CollectionType {
  collectionName: 'about_us_sections';
  info: {
    singularName: 'about-us-section';
    pluralName: 'about-us-sections';
    displayName: 'AboutUsSection';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    description: Attribute.Text;
    about_us_profiles: Attribute.Relation<
      'api::about-us-section.about-us-section',
      'oneToMany',
      'api::about-us-profile.about-us-profile'
    >;
    priority: Attribute.Integer & Attribute.DefaultTo<100>;
    columns: Attribute.Integer;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::about-us-section.about-us-section',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::about-us-section.about-us-section',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiActivityLogActivityLog extends Schema.CollectionType {
  collectionName: 'activity_logs';
  info: {
    singularName: 'activity-log';
    pluralName: 'activity-logs';
    displayName: 'ActivityLog';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    user: Attribute.Relation<
      'api::activity-log.activity-log',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    activity: Attribute.Enumeration<
      ['ArticleSubmit', 'ArticleApprove', 'ArticleReject', 'ArticlePublish']
    >;
    detail: Attribute.String;
    news_article: Attribute.Relation<
      'api::activity-log.activity-log',
      'oneToOne',
      'api::news-article.news-article'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::activity-log.activity-log',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::activity-log.activity-log',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiAffiliationAffiliation extends Schema.CollectionType {
  collectionName: 'affiliations';
  info: {
    singularName: 'affiliation';
    pluralName: 'affiliations';
    displayName: 'Affiliation';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    description: Attribute.Text;
    logo: Attribute.Media;
    slug: Attribute.UID<'api::affiliation.affiliation', 'name'>;
    seo: Attribute.Component<'shared.seo'>;
    website: Attribute.String;
    follow_affiliates: Attribute.Relation<
      'api::affiliation.affiliation',
      'oneToMany',
      'api::follow-affiliate.follow-affiliate'
    >;
    coverImage: Attribute.Media;
    albums: Attribute.Relation<
      'api::affiliation.affiliation',
      'oneToMany',
      'api::album.album'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::affiliation.affiliation',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::affiliation.affiliation',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiAlbumAlbum extends Schema.CollectionType {
  collectionName: 'albums';
  info: {
    singularName: 'album';
    pluralName: 'albums';
    displayName: 'Album';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    intro: Attribute.Text;
    story: Attribute.RichText;
    postcards: Attribute.Relation<
      'api::album.album',
      'oneToMany',
      'api::postcard.postcard'
    >;
    user: Attribute.Relation<
      'api::album.album',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    coverImage: Attribute.Media;
    seo: Attribute.Component<'shared.seo'>;
    isFeatured: Attribute.Boolean & Attribute.DefaultTo<false>;
    priority: Attribute.Integer & Attribute.DefaultTo<100>;
    avgPricePerPerson: Attribute.Decimal;
    bestMonth: Attribute.Component<'best-month.best-month', true>;
    isActive: Attribute.Boolean & Attribute.DefaultTo<false>;
    slug: Attribute.UID<'api::album.album', 'name'>;
    on_boarding: Attribute.Relation<
      'api::album.album',
      'oneToOne',
      'api::album-stage.album-stage'
    >;
    country: Attribute.Relation<
      'api::album.album',
      'oneToOne',
      'api::country.country'
    >;
    company: Attribute.Relation<
      'api::album.album',
      'manyToOne',
      'api::company.company'
    >;
    tourInfo: Attribute.RichText;
    pricesStartingAt: Attribute.String;
    numberOfNights: Attribute.String;
    bestTimetoTravel: Attribute.String;
    numberOfGuestsTitle: Attribute.String;
    numberOfGuestsValue: Attribute.String;
    directories: Attribute.Relation<
      'api::album.album',
      'manyToMany',
      'api::directory.directory'
    >;
    companySlug: Attribute.UID;
    album_themes: Attribute.Relation<
      'api::album.album',
      'oneToMany',
      'api::album-theme.album-theme'
    >;
    fixedDates: Attribute.String;
    additionalInfo: Attribute.Text;
    sustainability: Attribute.Text;
    website: Attribute.String;
    signature: Attribute.String;
    follow_albums: Attribute.Relation<
      'api::album.album',
      'oneToMany',
      'api::follow-album.follow-album'
    >;
    news_article: Attribute.Relation<
      'api::album.album',
      'oneToOne',
      'api::news-article.news-article'
    >;
    lat: Attribute.Float;
    long: Attribute.Float;
    placeId: Attribute.String;
    media_kit: Attribute.String;
    category: Attribute.Relation<
      'api::album.album',
      'manyToOne',
      'api::category.category'
    >;
    region: Attribute.Relation<
      'api::album.album',
      'manyToOne',
      'api::region.region'
    >;
    environment: Attribute.Relation<
      'api::album.album',
      'manyToOne',
      'api::environment.environment'
    >;
    cuisines: Attribute.Relation<
      'api::album.album',
      'oneToMany',
      'api::category.category'
    >;
    memories: Attribute.Relation<
      'api::album.album',
      'oneToMany',
      'api::memory.memory'
    >;
    date: Attribute.Date;
    assignTo: Attribute.Relation<
      'api::album.album',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    status: Attribute.Enumeration<
      ['draft', 'assigned', 'submit', 'rework', 'live']
    >;
    locationLink: Attribute.String;
    locality: Attribute.Relation<
      'api::album.album',
      'manyToOne',
      'api::locality.locality'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::album.album',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::album.album',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiAlbumSectionAlbumSection extends Schema.CollectionType {
  collectionName: 'album_sections';
  info: {
    singularName: 'album-section';
    pluralName: 'album-sections';
    displayName: 'Album Section';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    order: Attribute.Integer;
    hasSubsection: Attribute.Boolean & Attribute.DefaultTo<true>;
    hasSubTitle: Attribute.Boolean & Attribute.DefaultTo<true>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::album-section.album-section',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::album-section.album-section',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiAlbumStageAlbumStage extends Schema.CollectionType {
  collectionName: 'album_stages';
  info: {
    singularName: 'album-stage';
    pluralName: 'album-stages';
    displayName: 'OnBoarding';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    name: Attribute.String;
    album: Attribute.Relation<
      'api::album-stage.album-stage',
      'oneToOne',
      'api::album.album'
    >;
    key: Attribute.String;
    state: Attribute.Enumeration<
      [
        'tour-meta-story',
        'postcard-titles-upload',
        'postcard-titles-review',
        'postcard-stories-upload',
        'postcard-stories-review',
        'approved'
      ]
    >;
    tempProfile: Attribute.String;
    user: Attribute.Relation<
      'api::album-stage.album-stage',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::album-stage.album-stage',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::album-stage.album-stage',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiAlbumThemeAlbumTheme extends Schema.CollectionType {
  collectionName: 'album_themes';
  info: {
    singularName: 'album-theme';
    pluralName: 'album-themes';
    displayName: 'AlbumTheme';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::album-theme.album-theme',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::album-theme.album-theme',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiBookmarkBookmark extends Schema.CollectionType {
  collectionName: 'bookmarks';
  info: {
    singularName: 'bookmark';
    pluralName: 'bookmarks';
    displayName: 'Bookmark';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    user: Attribute.Relation<
      'api::bookmark.bookmark',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    postcard: Attribute.Relation<
      'api::bookmark.bookmark',
      'manyToOne',
      'api::postcard.postcard'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::bookmark.bookmark',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::bookmark.bookmark',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiCategoryCategory extends Schema.CollectionType {
  collectionName: 'categories';
  info: {
    singularName: 'category';
    pluralName: 'categories';
    displayName: 'Category';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    slug: Attribute.UID<'api::category.category', 'name'>;
    directory: Attribute.Relation<
      'api::category.category',
      'manyToOne',
      'api::directory.directory'
    >;
    albums: Attribute.Relation<
      'api::category.category',
      'oneToMany',
      'api::album.album'
    >;
    dx_cards: Attribute.Relation<
      'api::category.category',
      'oneToMany',
      'api::dx-card.dx-card'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::category.category',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::category.category',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiChatChat extends Schema.CollectionType {
  collectionName: 'chats';
  info: {
    singularName: 'chat';
    pluralName: 'chats';
    displayName: 'chat';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    message: Attribute.Text;
    type: Attribute.Enumeration<['user', 'bot']> & Attribute.DefaultTo<'user'>;
    user: Attribute.Relation<
      'api::chat.chat',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<'api::chat.chat', 'oneToOne', 'admin::user'> &
      Attribute.Private;
    updatedBy: Attribute.Relation<'api::chat.chat', 'oneToOne', 'admin::user'> &
      Attribute.Private;
  };
}

export interface ApiCityGuideCityGuide extends Schema.CollectionType {
  collectionName: 'city_guides';
  info: {
    singularName: 'city-guide';
    pluralName: 'city-guides';
    displayName: 'CityGuide';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    region: Attribute.Relation<
      'api::city-guide.city-guide',
      'manyToOne',
      'api::region.region'
    >;
    country: Attribute.Relation<
      'api::city-guide.city-guide',
      'manyToOne',
      'api::country.country'
    >;
    description: Attribute.Text;
    image: Attribute.Media;
    follow_city_guides: Attribute.Relation<
      'api::city-guide.city-guide',
      'oneToMany',
      'api::follow-city-guide.follow-city-guide'
    >;
    communityLink: Attribute.String;
    slug: Attribute.UID;
    status: Attribute.Enumeration<['draft', 'published']> &
      Attribute.DefaultTo<'draft'>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::city-guide.city-guide',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::city-guide.city-guide',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiCompanyCompany extends Schema.CollectionType {
  collectionName: 'companies';
  info: {
    singularName: 'company';
    pluralName: 'companies';
    displayName: 'Company';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    name: Attribute.String;
    users: Attribute.Relation<
      'api::company.company',
      'oneToMany',
      'plugin::users-permissions.user'
    >;
    albums: Attribute.Relation<
      'api::company.company',
      'oneToMany',
      'api::album.album'
    >;
    icon: Attribute.Media;
    follow_companies: Attribute.Relation<
      'api::company.company',
      'oneToMany',
      'api::follow-company.follow-company'
    >;
    website: Attribute.String;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::company.company',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::company.company',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiConfigConfig extends Schema.SingleType {
  collectionName: 'configs';
  info: {
    singularName: 'config';
    pluralName: 'configs';
    displayName: 'config';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    version: Attribute.Integer;
    mediaPath: Attribute.String;
    headerTitle: Attribute.String;
    headerSubTitle: Attribute.Text;
    showFeaturedAlbums: Attribute.Boolean & Attribute.DefaultTo<true>;
    showFeaturedPostcards: Attribute.Boolean & Attribute.DefaultTo<true>;
    maxFeaturedAlbums: Attribute.Integer & Attribute.DefaultTo<10>;
    maxFeaturedPostcards: Attribute.Integer & Attribute.DefaultTo<20>;
    sharedSeo: Attribute.Component<'shared.seo'>;
    publications: Attribute.Text;
    ourStoryDescription: Attribute.Text;
    supportLink: Attribute.String;
    featuredAlbums: Attribute.Relation<
      'api::config.config',
      'oneToMany',
      'api::album.album'
    >;
    featuredPostcards: Attribute.Relation<
      'api::config.config',
      'oneToMany',
      'api::postcard.postcard'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::config.config',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::config.config',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiContactUsContactUs extends Schema.CollectionType {
  collectionName: 'contact_uses';
  info: {
    singularName: 'contact-us';
    pluralName: 'contact-uses';
    displayName: 'ContactUs';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    firstName: Attribute.String;
    lastName: Attribute.String;
    email: Attribute.Email;
    countryCode: Attribute.Integer;
    phoneNumber: Attribute.BigInteger;
    question: Attribute.Text;
    status: Attribute.Enumeration<['open', 'inprogress', 'closed']>;
    user: Attribute.Relation<
      'api::contact-us.contact-us',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    album: Attribute.Relation<
      'api::contact-us.contact-us',
      'oneToOne',
      'api::album.album'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::contact-us.contact-us',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::contact-us.contact-us',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiContentReviewContentReview extends Schema.CollectionType {
  collectionName: 'content_reviews';
  info: {
    singularName: 'content-review';
    pluralName: 'content-reviews';
    displayName: 'ContentReview';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    review: Attribute.Text;
    news_article: Attribute.Relation<
      'api::content-review.content-review',
      'oneToOne',
      'api::news-article.news-article'
    >;
    user: Attribute.Relation<
      'api::content-review.content-review',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    status: Attribute.Enumeration<
      ['Submitted', 'Read', 'Approved', 'Rejected']
    > &
      Attribute.DefaultTo<'Submitted'>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::content-review.content-review',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::content-review.content-review',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiCountryCountry extends Schema.CollectionType {
  collectionName: 'countries';
  info: {
    singularName: 'country';
    pluralName: 'countries';
    displayName: 'country';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    slug: Attribute.UID<'api::country.country', 'name'>;
    code: Attribute.String;
    otherNames: Attribute.Component<'other-names.other-names', true>;
    continent: Attribute.Enumeration<
      ['AF', 'AS', 'AN', 'EU', 'NA', 'OC', 'SA']
    >;
    regions: Attribute.Relation<
      'api::country.country',
      'oneToMany',
      'api::region.region'
    >;
    memories: Attribute.Relation<
      'api::country.country',
      'oneToMany',
      'api::memory.memory'
    >;
    city_guides: Attribute.Relation<
      'api::country.country',
      'oneToMany',
      'api::city-guide.city-guide'
    >;
    coverImage: Attribute.Media;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::country.country',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::country.country',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiCuratedListingCuratedListing extends Schema.CollectionType {
  collectionName: 'curated_listings';
  info: {
    singularName: 'curated-listing';
    pluralName: 'curated-listings';
    displayName: 'Curated Listing';
    description: 'Postcard-curated /best/[slug] landing page (stays / themed retreats / experiences / itineraries).';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    slug: Attribute.UID<'api::curated-listing.curated-listing', 'title'> &
      Attribute.Required;
    archetype: Attribute.Enumeration<
      [
        'stays_in_city',
        'themed_retreats_by_region',
        'experiences_in_destination',
        'itineraries_in_destination'
      ]
    > &
      Attribute.Required;
    title: Attribute.String &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        maxLength: 120;
      }>;
    seoTitle: Attribute.String &
      Attribute.SetMinMaxLength<{
        maxLength: 70;
      }>;
    seoDescription: Attribute.Text &
      Attribute.Required &
      Attribute.SetMinMaxLength<{
        maxLength: 160;
      }>;
    editorialIntro: Attribute.RichText & Attribute.Required;
    editorialClose: Attribute.RichText;
    byline: Attribute.Relation<
      'api::curated-listing.curated-listing',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    featuredImage: Attribute.Media & Attribute.Required;
    filters: Attribute.JSON & Attribute.Required;
    relatedListings: Attribute.Relation<
      'api::curated-listing.curated-listing',
      'oneToMany',
      'api::curated-listing.curated-listing'
    >;
    noindex: Attribute.Boolean & Attribute.DefaultTo<false>;
    priority: Attribute.Decimal &
      Attribute.SetMinMax<{
        min: 0;
        max: 1;
      }> &
      Attribute.DefaultTo<0.8>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::curated-listing.curated-listing',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::curated-listing.curated-listing',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiDeletionDeletion extends Schema.CollectionType {
  collectionName: 'deletions';
  info: {
    singularName: 'deletion';
    pluralName: 'deletions';
    displayName: 'Deletion';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    message: Attribute.String;
    fbId: Attribute.String;
    user: Attribute.Relation<
      'api::deletion.deletion',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::deletion.deletion',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::deletion.deletion',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiDestinationExpertDestinationExpert
  extends Schema.CollectionType {
  collectionName: 'destination_experts';
  info: {
    singularName: 'destination-expert';
    pluralName: 'destination-experts';
    displayName: 'Destination Expert';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    user: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    name: Attribute.String;
    title: Attribute.String;
    coverImage: Attribute.Media;
    country: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToOne',
      'api::country.country'
    >;
    tagLine: Attribute.Text;
    quotes: Attribute.Component<'destination-expert.quotes'>;
    founderMessage: Attribute.Component<'destination-expert.founder-message'>;
    dxSections: Attribute.Component<'destination-expert.dx-sections', true>;
    testimonials: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToMany',
      'api::testimonial.testimonial'
    >;
    status: Attribute.Enumeration<['draft', 'published']> &
      Attribute.DefaultTo<'draft'>;
    dx_cards: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToMany',
      'api::dx-card.dx-card'
    >;
    region: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToOne',
      'api::region.region'
    >;
    travelogues: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToMany',
      'api::travelogue.travelogue'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::destination-expert.destination-expert',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiDirectoryDirectory extends Schema.CollectionType {
  collectionName: 'directories';
  info: {
    singularName: 'directory';
    pluralName: 'directories';
    displayName: 'Directory';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    description: Attribute.Text;
    albums: Attribute.Relation<
      'api::directory.directory',
      'manyToMany',
      'api::album.album'
    >;
    logo: Attribute.Media;
    slug: Attribute.UID<'api::directory.directory', 'name'>;
    seo: Attribute.Component<'shared.seo'>;
    label: Attribute.String;
    categories: Attribute.Relation<
      'api::directory.directory',
      'oneToMany',
      'api::category.category'
    >;
    environments: Attribute.Relation<
      'api::directory.directory',
      'oneToMany',
      'api::environment.environment'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::directory.directory',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::directory.directory',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiDxCardDxCard extends Schema.CollectionType {
  collectionName: 'dx_cards';
  info: {
    singularName: 'dx-card';
    pluralName: 'dx-cards';
    displayName: 'dxCard';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    coverImage: Attribute.Media;
    story: Attribute.RichText;
    country: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToOne',
      'api::country.country'
    >;
    region: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToOne',
      'api::region.region'
    >;
    postcard: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToOne',
      'api::postcard.postcard'
    >;
    album: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToOne',
      'api::album.album'
    >;
    users_permissions_user: Attribute.Relation<
      'api::dx-card.dx-card',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    dx_card_type: Attribute.Relation<
      'api::dx-card.dx-card',
      'manyToOne',
      'api::dx-card-type.dx-card-type'
    >;
    destination_expert: Attribute.Relation<
      'api::dx-card.dx-card',
      'manyToOne',
      'api::destination-expert.destination-expert'
    >;
    intro: Attribute.Text;
    tag_group: Attribute.Relation<
      'api::dx-card.dx-card',
      'manyToOne',
      'api::tag-group.tag-group'
    >;
    tags: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToMany',
      'api::tag.tag'
    >;
    environment: Attribute.Relation<
      'api::dx-card.dx-card',
      'manyToOne',
      'api::environment.environment'
    >;
    category: Attribute.Relation<
      'api::dx-card.dx-card',
      'manyToOne',
      'api::category.category'
    >;
    memories: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToMany',
      'api::memory.memory'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::dx-card.dx-card',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiDxCardTypeDxCardType extends Schema.CollectionType {
  collectionName: 'dx_card_types';
  info: {
    singularName: 'dx-card-type';
    pluralName: 'dx-card-types';
    displayName: 'dxCardType';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    dx_cards: Attribute.Relation<
      'api::dx-card-type.dx-card-type',
      'oneToMany',
      'api::dx-card.dx-card'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::dx-card-type.dx-card-type',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::dx-card-type.dx-card-type',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiDxSectionDxSection extends Schema.CollectionType {
  collectionName: 'dx_sections';
  info: {
    singularName: 'dx-section';
    pluralName: 'dx-sections';
    displayName: 'DXSection';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.String;
    priority: Attribute.Integer;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::dx-section.dx-section',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::dx-section.dx-section',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiEnvironmentEnvironment extends Schema.CollectionType {
  collectionName: 'environments';
  info: {
    singularName: 'environment';
    pluralName: 'environments';
    displayName: 'Environment';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    directory: Attribute.Relation<
      'api::environment.environment',
      'manyToOne',
      'api::directory.directory'
    >;
    albums: Attribute.Relation<
      'api::environment.environment',
      'oneToMany',
      'api::album.album'
    >;
    dx_cards: Attribute.Relation<
      'api::environment.environment',
      'oneToMany',
      'api::dx-card.dx-card'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::environment.environment',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::environment.environment',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiEventEvent extends Schema.CollectionType {
  collectionName: 'events';
  info: {
    singularName: 'event';
    pluralName: 'events';
    displayName: 'Event';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    event_master: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'api::event-master.event-master'
    >;
    user: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    meta: Attribute.JSON;
    ipAddress: Attribute.String;
    ipCountry: Attribute.String;
    album: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'api::album.album'
    >;
    postcard: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'api::postcard.postcard'
    >;
    podcast: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'api::podcast.podcast'
    >;
    url: Attribute.String;
    following: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    searchData: Attribute.JSON;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::event.event',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiEventMasterEventMaster extends Schema.CollectionType {
  collectionName: 'event_masters';
  info: {
    singularName: 'event-master';
    pluralName: 'event-masters';
    displayName: 'Event Master';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    code: Attribute.String;
    active: Attribute.Boolean & Attribute.DefaultTo<true>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::event-master.event-master',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::event-master.event-master',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiFollowFollow extends Schema.CollectionType {
  collectionName: 'follows';
  info: {
    singularName: 'follow';
    pluralName: 'follows';
    displayName: 'Follow';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    follower: Attribute.Relation<
      'api::follow.follow',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    following: Attribute.Relation<
      'api::follow.follow',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::follow.follow',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::follow.follow',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiFollowAffiliateFollowAffiliate
  extends Schema.CollectionType {
  collectionName: 'follow_affiliates';
  info: {
    singularName: 'follow-affiliate';
    pluralName: 'follow-affiliates';
    displayName: 'Follow Affiliate';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    follower: Attribute.Relation<
      'api::follow-affiliate.follow-affiliate',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    affiliation: Attribute.Relation<
      'api::follow-affiliate.follow-affiliate',
      'manyToOne',
      'api::affiliation.affiliation'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::follow-affiliate.follow-affiliate',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::follow-affiliate.follow-affiliate',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiFollowAlbumFollowAlbum extends Schema.CollectionType {
  collectionName: 'follow_albums';
  info: {
    singularName: 'follow-album';
    pluralName: 'follow-albums';
    displayName: 'Follow Album';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    follower: Attribute.Relation<
      'api::follow-album.follow-album',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    album: Attribute.Relation<
      'api::follow-album.follow-album',
      'manyToOne',
      'api::album.album'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::follow-album.follow-album',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::follow-album.follow-album',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiFollowCityGuideFollowCityGuide
  extends Schema.CollectionType {
  collectionName: 'follow_city_guides';
  info: {
    singularName: 'follow-city-guide';
    pluralName: 'follow-city-guides';
    displayName: 'FollowCityGuide';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    users_permissions_user: Attribute.Relation<
      'api::follow-city-guide.follow-city-guide',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    city_guide: Attribute.Relation<
      'api::follow-city-guide.follow-city-guide',
      'manyToOne',
      'api::city-guide.city-guide'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::follow-city-guide.follow-city-guide',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::follow-city-guide.follow-city-guide',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiFollowCompanyFollowCompany extends Schema.CollectionType {
  collectionName: 'follow_companies';
  info: {
    singularName: 'follow-company';
    pluralName: 'follow-companies';
    displayName: 'Follow Company';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    follower: Attribute.Relation<
      'api::follow-company.follow-company',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    company: Attribute.Relation<
      'api::follow-company.follow-company',
      'manyToOne',
      'api::company.company'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::follow-company.follow-company',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::follow-company.follow-company',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiFollowTagFollowTag extends Schema.CollectionType {
  collectionName: 'follow_tags';
  info: {
    singularName: 'follow-tag';
    pluralName: 'follow-tags';
    displayName: 'Follow Tag';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    follower: Attribute.Relation<
      'api::follow-tag.follow-tag',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    tag: Attribute.Relation<
      'api::follow-tag.follow-tag',
      'manyToOne',
      'api::tag.tag'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::follow-tag.follow-tag',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::follow-tag.follow-tag',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiLocalityLocality extends Schema.CollectionType {
  collectionName: 'localities';
  info: {
    singularName: 'locality';
    pluralName: 'localities';
    displayName: 'locality';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String & Attribute.Required & Attribute.Unique;
    region: Attribute.Relation<
      'api::locality.locality',
      'manyToOne',
      'api::region.region'
    >;
    albums: Attribute.Relation<
      'api::locality.locality',
      'oneToMany',
      'api::album.album'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::locality.locality',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::locality.locality',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiMemoryMemory extends Schema.CollectionType {
  collectionName: 'memories';
  info: {
    singularName: 'memory';
    pluralName: 'memories';
    displayName: 'memory';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    isPrivate: Attribute.Boolean;
    intro: Attribute.Text;
    slug: Attribute.UID<'api::memory.memory', 'name'>;
    date: Attribute.Date;
    album: Attribute.Relation<
      'api::memory.memory',
      'manyToOne',
      'api::album.album'
    >;
    postcard: Attribute.Relation<
      'api::memory.memory',
      'manyToOne',
      'api::postcard.postcard'
    >;
    dx_card: Attribute.Relation<
      'api::memory.memory',
      'manyToOne',
      'api::dx-card.dx-card'
    >;
    user: Attribute.Relation<
      'api::memory.memory',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    gallery: Attribute.Media;
    region: Attribute.Relation<
      'api::memory.memory',
      'manyToOne',
      'api::region.region'
    >;
    country: Attribute.Relation<
      'api::memory.memory',
      'manyToOne',
      'api::country.country'
    >;
    internalUrl: Attribute.String;
    externalUrl: Attribute.String;
    signature: Attribute.String;
    shareType: Attribute.Enumeration<['private', 'public', 'selected']>;
    tagged_users: Attribute.Relation<
      'api::memory.memory',
      'oneToMany',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::memory.memory',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::memory.memory',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiMonthMonth extends Schema.CollectionType {
  collectionName: 'months';
  info: {
    singularName: 'month';
    pluralName: 'months';
    displayName: 'Month';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    Code: Attribute.String;
    property_itinerary: Attribute.Relation<
      'api::month.month',
      'manyToOne',
      'api::property-itinerary.property-itinerary'
    >;
    travelogue: Attribute.Relation<
      'api::month.month',
      'manyToOne',
      'api::travelogue.travelogue'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::month.month',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::month.month',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiNewsArticleNewsArticle extends Schema.CollectionType {
  collectionName: 'news_articles';
  info: {
    singularName: 'news-article';
    pluralName: 'news-articles';
    displayName: 'NewsArticle';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.String;
    image: Attribute.Media;
    description: Attribute.Text;
    link: Attribute.String;
    priority: Attribute.Integer & Attribute.DefaultTo<10>;
    publishedDate: Attribute.DateTime;
    blog: Attribute.Component<'blog.blog', true>;
    videoURL: Attribute.String;
    video: Attribute.Media;
    creator: Attribute.Relation<
      'api::news-article.news-article',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    album: Attribute.Relation<
      'api::news-article.news-article',
      'oneToOne',
      'api::album.album'
    >;
    block: Attribute.Component<'album-block.album-block', true>;
    status: Attribute.Enumeration<
      [
        'draft',
        'submitted',
        'editor-approved',
        'editor-rejected',
        'eic-approved',
        'eic-rejected',
        'published'
      ]
    >;
    assignto: Attribute.Relation<
      'api::news-article.news-article',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::news-article.news-article',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::news-article.news-article',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiPodcastPodcast extends Schema.CollectionType {
  collectionName: 'podcasts';
  info: {
    singularName: 'podcast';
    pluralName: 'podcasts';
    displayName: 'Podcast';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.String;
    slug: Attribute.UID;
    description: Attribute.Text;
    album: Attribute.Relation<
      'api::podcast.podcast',
      'oneToOne',
      'api::album.album'
    >;
    pubDate: Attribute.Date;
    user: Attribute.Relation<
      'api::podcast.podcast',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    preview: Attribute.Media;
    spotifyUrl: Attribute.Text;
    appleUrl: Attribute.Text;
    googleUrl: Attribute.Text;
    podcastUrl: Attribute.Text;
    thumbnail: Attribute.Media;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::podcast.podcast',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::podcast.podcast',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiPostcardPostcard extends Schema.CollectionType {
  collectionName: 'postcards';
  info: {
    singularName: 'postcard';
    pluralName: 'postcards';
    displayName: 'Postcard';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    intro: Attribute.Text;
    slug: Attribute.UID<'api::postcard.postcard', 'name'>;
    story: Attribute.RichText;
    user: Attribute.Relation<
      'api::postcard.postcard',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    country: Attribute.Relation<
      'api::postcard.postcard',
      'oneToOne',
      'api::country.country'
    >;
    album: Attribute.Relation<
      'api::postcard.postcard',
      'manyToOne',
      'api::album.album'
    >;
    tags: Attribute.Relation<
      'api::postcard.postcard',
      'oneToMany',
      'api::tag.tag'
    >;
    copyright: Attribute.String;
    articleURL: Attribute.String;
    isFeatured: Attribute.Boolean & Attribute.DefaultTo<false>;
    coverImage: Attribute.Media;
    isComplete: Attribute.Boolean & Attribute.DefaultTo<false>;
    priority: Attribute.Integer & Attribute.DefaultTo<20>;
    isFounderStory: Attribute.Boolean & Attribute.DefaultTo<false>;
    bookmarks: Attribute.Relation<
      'api::postcard.postcard',
      'oneToMany',
      'api::bookmark.bookmark'
    >;
    album_themes: Attribute.Relation<
      'api::postcard.postcard',
      'oneToMany',
      'api::album-theme.album-theme'
    >;
    memories: Attribute.Relation<
      'api::postcard.postcard',
      'oneToMany',
      'api::memory.memory'
    >;
    property_itineraries: Attribute.Relation<
      'api::postcard.postcard',
      'manyToMany',
      'api::property-itinerary.property-itinerary'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::postcard.postcard',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::postcard.postcard',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiProfileProfile extends Schema.CollectionType {
  collectionName: 'profiles';
  info: {
    singularName: 'profile';
    pluralName: 'profiles';
    displayName: 'Profile';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    travelStyle: Attribute.Enumeration<
      ['Mindful', 'Slow-paced', 'Sustainable']
    >;
    interests: Attribute.Enumeration<
      ['Culture', 'Nature', 'Local cuisine', 'Wellness']
    >;
    destinations: Attribute.Enumeration<
      ['Europe', 'Asia', 'South America', 'Africa']
    >;
    travelFrequency: Attribute.Enumeration<
      ['One to Two trips', 'Two or more trips']
    >;
    accommodation: Attribute.Enumeration<
      ['Eco-friendly', 'Local guesthouses or home-stays', 'Boutique hotels']
    >;
    transportation: Attribute.Enumeration<
      ['Public transportation', 'Walking or cycling', 'Car-sharing']
    >;
    activities: Attribute.Enumeration<
      [
        'Cultural tours',
        'Hiking or nature walks',
        'Yoga or meditation retreats',
        'Cooking classes or food tours',
        'Volunteer opportunities'
      ]
    >;
    travelBudget: Attribute.Enumeration<
      ['Moderate', 'Willing to spend more for unique experiences']
    >;
    user: Attribute.Relation<
      'api::profile.profile',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::profile.profile',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::profile.profile',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiPropertyItineraryPropertyItinerary
  extends Schema.CollectionType {
  collectionName: 'property_itineraries';
  info: {
    singularName: 'property-itinerary';
    pluralName: 'property-itineraries';
    displayName: 'propertyItinerary';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.Text;
    description: Attribute.Text;
    coverImage: Attribute.Media;
    numberOfDays: Attribute.Integer;
    numberOfNights: Attribute.Integer;
    price: Attribute.Integer;
    postcards: Attribute.Relation<
      'api::property-itinerary.property-itinerary',
      'manyToMany',
      'api::postcard.postcard'
    >;
    album: Attribute.Relation<
      'api::property-itinerary.property-itinerary',
      'oneToOne',
      'api::album.album'
    >;
    best_time_to_visits: Attribute.Relation<
      'api::property-itinerary.property-itinerary',
      'oneToMany',
      'api::month.month'
    >;
    status: Attribute.Enumeration<
      ['draft', 'deckBuild', 'deckFreeze', 'onTrip', 'complete']
    >;
    country: Attribute.Relation<
      'api::property-itinerary.property-itinerary',
      'oneToOne',
      'api::country.country'
    >;
    dayWiseItinerary: Attribute.RichText;
    termsAndConditions: Attribute.RichText;
    priceType: Attribute.Enumeration<['per person', 'twin sharing']> &
      Attribute.DefaultTo<'per person'>;
    slug: Attribute.UID<'api::property-itinerary.property-itinerary', 'title'>;
    createdByUser: Attribute.Relation<
      'api::property-itinerary.property-itinerary',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::property-itinerary.property-itinerary',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::property-itinerary.property-itinerary',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiPublicationPublication extends Schema.CollectionType {
  collectionName: 'publications';
  info: {
    singularName: 'publication';
    pluralName: 'publications';
    displayName: 'Publication';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    validationString: Attribute.String;
    priority: Attribute.Integer & Attribute.DefaultTo<100>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::publication.publication',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::publication.publication',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiRegionRegion extends Schema.CollectionType {
  collectionName: 'regions';
  info: {
    singularName: 'region';
    pluralName: 'regions';
    displayName: 'Region';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String & Attribute.Unique;
    country: Attribute.Relation<
      'api::region.region',
      'manyToOne',
      'api::country.country'
    >;
    albums: Attribute.Relation<
      'api::region.region',
      'oneToMany',
      'api::album.album'
    >;
    memories: Attribute.Relation<
      'api::region.region',
      'oneToMany',
      'api::memory.memory'
    >;
    city_guides: Attribute.Relation<
      'api::region.region',
      'oneToMany',
      'api::city-guide.city-guide'
    >;
    locality: Attribute.Relation<
      'api::region.region',
      'oneToMany',
      'api::locality.locality'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::region.region',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::region.region',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiRestaurantRestaurant extends Schema.CollectionType {
  collectionName: 'restaurants';
  info: {
    singularName: 'restaurant';
    pluralName: 'restaurants';
    displayName: 'Restaurant';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.String;
    intro: Attribute.Text;
    story: Attribute.Text;
    restaurant_types: Attribute.Relation<
      'api::restaurant.restaurant',
      'oneToMany',
      'api::restaurant-type.restaurant-type'
    >;
    country: Attribute.Relation<
      'api::restaurant.restaurant',
      'oneToOne',
      'api::country.country'
    >;
    region: Attribute.Relation<
      'api::restaurant.restaurant',
      'oneToOne',
      'api::region.region'
    >;
    coverImage: Attribute.Media;
    users_permissions_user: Attribute.Relation<
      'api::restaurant.restaurant',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::restaurant.restaurant',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::restaurant.restaurant',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiRestaurantTypeRestaurantType extends Schema.CollectionType {
  collectionName: 'restaurant_types';
  info: {
    singularName: 'restaurant-type';
    pluralName: 'restaurant-types';
    displayName: 'RestaurantType';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.String;
    restaurant: Attribute.Relation<
      'api::restaurant-type.restaurant-type',
      'manyToOne',
      'api::restaurant.restaurant'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::restaurant-type.restaurant-type',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::restaurant-type.restaurant-type',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiSessionSession extends Schema.CollectionType {
  collectionName: 'sessions';
  info: {
    singularName: 'session';
    pluralName: 'sessions';
    displayName: 'Session';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    ipAddress: Attribute.String;
    params: Attribute.JSON;
    url: Attribute.String;
    ipCountry: Attribute.String;
    referrer: Attribute.String;
    user: Attribute.Relation<
      'api::session.session',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    userdevice: Attribute.Relation<
      'api::session.session',
      'oneToOne',
      'api::userdevice.userdevice'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::session.session',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::session.session',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiSignUpSignUp extends Schema.CollectionType {
  collectionName: 'sign_ups';
  info: {
    singularName: 'sign-up';
    pluralName: 'sign-ups';
    displayName: 'SignUp';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    email: Attribute.Email;
    accessCode: Attribute.String;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::sign-up.sign-up',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::sign-up.sign-up',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiTagTag extends Schema.CollectionType {
  collectionName: 'tags';
  info: {
    singularName: 'tag';
    pluralName: 'tags';
    displayName: 'Tag';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    name: Attribute.String & Attribute.Required & Attribute.Unique;
    tag_group: Attribute.Relation<
      'api::tag.tag',
      'manyToOne',
      'api::tag-group.tag-group'
    >;
    follow_tags: Attribute.Relation<
      'api::tag.tag',
      'oneToMany',
      'api::follow-tag.follow-tag'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<'api::tag.tag', 'oneToOne', 'admin::user'> &
      Attribute.Private;
    updatedBy: Attribute.Relation<'api::tag.tag', 'oneToOne', 'admin::user'> &
      Attribute.Private;
  };
}

export interface ApiTagGroupTagGroup extends Schema.CollectionType {
  collectionName: 'tag_groups';
  info: {
    singularName: 'tag-group';
    pluralName: 'tag-groups';
    displayName: 'TagGroup';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    tags: Attribute.Relation<
      'api::tag-group.tag-group',
      'oneToMany',
      'api::tag.tag'
    >;
    priority: Attribute.Integer;
    dx_cards: Attribute.Relation<
      'api::tag-group.tag-group',
      'oneToMany',
      'api::dx-card.dx-card'
    >;
    coverImage: Attribute.Media;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::tag-group.tag-group',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::tag-group.tag-group',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiTestimonialTestimonial extends Schema.CollectionType {
  collectionName: 'testimonials';
  info: {
    singularName: 'testimonial';
    pluralName: 'testimonials';
    displayName: 'Testimonial';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    message: Attribute.Text;
    name: Attribute.String;
    title: Attribute.String;
    imageUrl: Attribute.String;
    location: Attribute.String;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::testimonial.testimonial',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::testimonial.testimonial',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiTravelogueTravelogue extends Schema.CollectionType {
  collectionName: 'travelogues';
  info: {
    singularName: 'travelogue';
    pluralName: 'travelogues';
    displayName: 'Travelogue';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.String;
    user: Attribute.Relation<
      'api::travelogue.travelogue',
      'manyToOne',
      'plugin::users-permissions.user'
    >;
    destination_expert: Attribute.Relation<
      'api::travelogue.travelogue',
      'manyToOne',
      'api::destination-expert.destination-expert'
    >;
    itinerary_block: Attribute.Component<'itinerary-item.itinerary-item', true>;
    slug: Attribute.UID<'api::travelogue.travelogue', 'title'>;
    status: Attribute.Enumeration<
      ['draft', 'deckBuild', 'deckFreeze', 'onTrip', 'complete']
    >;
    startDate: Attribute.Date;
    endDate: Attribute.Date;
    isTemplate: Attribute.Boolean;
    description: Attribute.Text;
    numberOfDays: Attribute.Integer;
    numberOfNights: Attribute.Integer;
    price: Attribute.Integer;
    coverImage: Attribute.Media;
    best_time_to_visits: Attribute.Relation<
      'api::travelogue.travelogue',
      'oneToMany',
      'api::month.month'
    >;
    country: Attribute.Relation<
      'api::travelogue.travelogue',
      'oneToOne',
      'api::country.country'
    >;
    dayWiseItinerary: Attribute.RichText;
    termsAndConditions: Attribute.RichText;
    priceType: Attribute.Enumeration<['per person', 'twin sharing']> &
      Attribute.DefaultTo<'per person'>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::travelogue.travelogue',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::travelogue.travelogue',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiUiComponentUiComponent extends Schema.CollectionType {
  collectionName: 'ui_components';
  info: {
    singularName: 'ui-component';
    pluralName: 'ui-components';
    displayName: 'UiComponent';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    title: Attribute.Text;
    subtitle: Attribute.Text;
    type: Attribute.Enumeration<
      [
        'intro',
        'signup',
        'countries',
        'postcards',
        'albums',
        'did_you_know',
        'news_letter',
        'footer'
      ]
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::ui-component.ui-component',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::ui-component.ui-component',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiUserTypeUserType extends Schema.CollectionType {
  collectionName: 'user_types';
  info: {
    singularName: 'user-type';
    pluralName: 'user-types';
    displayName: 'UserType';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    name: Attribute.String;
    slug: Attribute.UID<'api::user-type.user-type', 'name'>;
    isDefault: Attribute.Boolean & Attribute.DefaultTo<false>;
    isCreator: Attribute.Boolean & Attribute.DefaultTo<false>;
    isAdmin: Attribute.Boolean & Attribute.DefaultTo<false>;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::user-type.user-type',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::user-type.user-type',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiUserdeviceUserdevice extends Schema.CollectionType {
  collectionName: 'userdevices';
  info: {
    singularName: 'userdevice';
    pluralName: 'userdevices';
    displayName: 'Userdevice';
    description: '';
  };
  options: {
    draftAndPublish: false;
  };
  attributes: {
    fcmtoken: Attribute.String;
    model: Attribute.String;
    manufacturer: Attribute.String;
    os: Attribute.String;
    osVersion: Attribute.String;
    isMobile: Attribute.Boolean & Attribute.DefaultTo<false>;
    userAgent: Attribute.String;
    user: Attribute.Relation<
      'api::userdevice.userdevice',
      'oneToOne',
      'plugin::users-permissions.user'
    >;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::userdevice.userdevice',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::userdevice.userdevice',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

export interface ApiWaitingListWaitingList extends Schema.CollectionType {
  collectionName: 'waiting_lists';
  info: {
    singularName: 'waiting-list';
    pluralName: 'waiting-lists';
    displayName: 'Waiting List';
    description: '';
  };
  options: {
    draftAndPublish: true;
  };
  attributes: {
    username: Attribute.String;
    email: Attribute.Email;
    status: Attribute.Enumeration<['waiting', 'activated', 'rejected']> &
      Attribute.DefaultTo<'waiting'>;
    country: Attribute.Relation<
      'api::waiting-list.waiting-list',
      'oneToOne',
      'api::country.country'
    >;
    city: Attribute.String;
    firstName: Attribute.String;
    lastName: Attribute.String;
    createdAt: Attribute.DateTime;
    updatedAt: Attribute.DateTime;
    publishedAt: Attribute.DateTime;
    createdBy: Attribute.Relation<
      'api::waiting-list.waiting-list',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
    updatedBy: Attribute.Relation<
      'api::waiting-list.waiting-list',
      'oneToOne',
      'admin::user'
    > &
      Attribute.Private;
  };
}

declare module '@strapi/types' {
  export module Shared {
    export interface ContentTypes {
      'admin::permission': AdminPermission;
      'admin::user': AdminUser;
      'admin::role': AdminRole;
      'admin::api-token': AdminApiToken;
      'admin::api-token-permission': AdminApiTokenPermission;
      'admin::transfer-token': AdminTransferToken;
      'admin::transfer-token-permission': AdminTransferTokenPermission;
      'plugin::upload.file': PluginUploadFile;
      'plugin::upload.folder': PluginUploadFolder;
      'plugin::users-permissions.permission': PluginUsersPermissionsPermission;
      'plugin::users-permissions.role': PluginUsersPermissionsRole;
      'plugin::users-permissions.user': PluginUsersPermissionsUser;
      'plugin::email-designer.email-template': PluginEmailDesignerEmailTemplate;
      'plugin::website-builder.log': PluginWebsiteBuilderLog;
      'plugin::chartbrew.chartbrew': PluginChartbrewChartbrew;
      'plugin::i18n.locale': PluginI18NLocale;
      'plugin::comments.comment': PluginCommentsComment;
      'plugin::comments.comment-report': PluginCommentsCommentReport;
      'api::about-us-profile.about-us-profile': ApiAboutUsProfileAboutUsProfile;
      'api::about-us-section.about-us-section': ApiAboutUsSectionAboutUsSection;
      'api::activity-log.activity-log': ApiActivityLogActivityLog;
      'api::affiliation.affiliation': ApiAffiliationAffiliation;
      'api::album.album': ApiAlbumAlbum;
      'api::album-section.album-section': ApiAlbumSectionAlbumSection;
      'api::album-stage.album-stage': ApiAlbumStageAlbumStage;
      'api::album-theme.album-theme': ApiAlbumThemeAlbumTheme;
      'api::bookmark.bookmark': ApiBookmarkBookmark;
      'api::category.category': ApiCategoryCategory;
      'api::chat.chat': ApiChatChat;
      'api::city-guide.city-guide': ApiCityGuideCityGuide;
      'api::company.company': ApiCompanyCompany;
      'api::config.config': ApiConfigConfig;
      'api::contact-us.contact-us': ApiContactUsContactUs;
      'api::content-review.content-review': ApiContentReviewContentReview;
      'api::country.country': ApiCountryCountry;
      'api::curated-listing.curated-listing': ApiCuratedListingCuratedListing;
      'api::deletion.deletion': ApiDeletionDeletion;
      'api::destination-expert.destination-expert': ApiDestinationExpertDestinationExpert;
      'api::directory.directory': ApiDirectoryDirectory;
      'api::dx-card.dx-card': ApiDxCardDxCard;
      'api::dx-card-type.dx-card-type': ApiDxCardTypeDxCardType;
      'api::dx-section.dx-section': ApiDxSectionDxSection;
      'api::environment.environment': ApiEnvironmentEnvironment;
      'api::event.event': ApiEventEvent;
      'api::event-master.event-master': ApiEventMasterEventMaster;
      'api::follow.follow': ApiFollowFollow;
      'api::follow-affiliate.follow-affiliate': ApiFollowAffiliateFollowAffiliate;
      'api::follow-album.follow-album': ApiFollowAlbumFollowAlbum;
      'api::follow-city-guide.follow-city-guide': ApiFollowCityGuideFollowCityGuide;
      'api::follow-company.follow-company': ApiFollowCompanyFollowCompany;
      'api::follow-tag.follow-tag': ApiFollowTagFollowTag;
      'api::locality.locality': ApiLocalityLocality;
      'api::memory.memory': ApiMemoryMemory;
      'api::month.month': ApiMonthMonth;
      'api::news-article.news-article': ApiNewsArticleNewsArticle;
      'api::podcast.podcast': ApiPodcastPodcast;
      'api::postcard.postcard': ApiPostcardPostcard;
      'api::profile.profile': ApiProfileProfile;
      'api::property-itinerary.property-itinerary': ApiPropertyItineraryPropertyItinerary;
      'api::publication.publication': ApiPublicationPublication;
      'api::region.region': ApiRegionRegion;
      'api::restaurant.restaurant': ApiRestaurantRestaurant;
      'api::restaurant-type.restaurant-type': ApiRestaurantTypeRestaurantType;
      'api::session.session': ApiSessionSession;
      'api::sign-up.sign-up': ApiSignUpSignUp;
      'api::tag.tag': ApiTagTag;
      'api::tag-group.tag-group': ApiTagGroupTagGroup;
      'api::testimonial.testimonial': ApiTestimonialTestimonial;
      'api::travelogue.travelogue': ApiTravelogueTravelogue;
      'api::ui-component.ui-component': ApiUiComponentUiComponent;
      'api::user-type.user-type': ApiUserTypeUserType;
      'api::userdevice.userdevice': ApiUserdeviceUserdevice;
      'api::waiting-list.waiting-list': ApiWaitingListWaitingList;
    }
  }
}
