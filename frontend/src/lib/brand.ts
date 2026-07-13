// LegalEdge brand string constants (SPEC §7.5).
//
// STRING CONSTANTS ONLY — do NOT import PNG assets here. Logo/mark images, if
// used, are referenced directly by the components that render them (e.g. from
// /src/assets or public), keeping this module free of bundler-hashed imports so
// it stays a pure, tree-shakeable constants file.

export const BRAND_NAME = 'LegalEdge';
export const BRAND_PARENT = 'Traxccel';
export const BRAND_PRODUCT = 'LegalEdge — Client Intake';
export const BRAND_TAGLINE = 'Client intake, captured the moment they call.';

/** Human-formatted intake phone number for display. */
export const INTAKE_PHONE = '+1 (415) 555-0100';
/** Dial-ready form for <a href="tel:..."> links. */
export const INTAKE_PHONE_TEL = '+14155550100';
