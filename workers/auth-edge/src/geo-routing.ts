interface GeoConfig {
  preferredRegions: Record<string, string>;
  defaultOrigin: string;
}

interface CfProperties {
  colo?: string;
  country?: string;
  continent?: string;
  city?: string;
  region?: string;
  timezone?: string;
  latitude?: string;
  longitude?: string;
}

/**
 * Default geo routing configuration
 */
export const DEFAULT_GEO_CONFIG: GeoConfig = {
  preferredRegions: {
    // Country-specific overrides (if you have regional deployments)
    // 'US': 'https://us.api.kortix.ai',
    // 'DE': 'https://eu.api.kortix.ai',
    // 'JP': 'https://ap.api.kortix.ai',
  },
  defaultOrigin: 'https://api.kortix.ai',
};

/**
 * Continent-based routing map
 */
const CONTINENT_ROUTES: Record<string, string> = {
  'NA': 'https://us.api.kortix.ai',   // North America
  'SA': 'https://us.api.kortix.ai',   // South America (route to US)
  'EU': 'https://eu.api.kortix.ai',   // Europe
  'AF': 'https://eu.api.kortix.ai',   // Africa (route to EU)
  'AS': 'https://ap.api.kortix.ai',   // Asia
  'OC': 'https://ap.api.kortix.ai',   // Oceania (route to AP)
  'AN': 'https://us.api.kortix.ai',   // Antarctica (route to US, unlikely)
};

/**
 * Route requests to nearest origin based on client location
 */
export function getOptimalOrigin(request: Request, config: GeoConfig = DEFAULT_GEO_CONFIG): string {
  const cf = request.cf as CfProperties | undefined;
  if (!cf) return config.defaultOrigin;

  const continent = cf.continent;
  const country = cf.country;

  // Check country-specific routing first
  if (country && config.preferredRegions[country]) {
    return config.preferredRegions[country];
  }

  // Fall back to continent-based routing
  if (continent && CONTINENT_ROUTES[continent]) {
    return CONTINENT_ROUTES[continent];
  }

  return config.defaultOrigin;
}

/**
 * Get geo information from request for logging/analytics
 */
export function getGeoInfo(request: Request): {
  country: string;
  continent: string;
  city: string;
  colo: string;
  timezone: string;
} {
  const cf = request.cf as CfProperties | undefined;
  
  return {
    country: cf?.country || 'unknown',
    continent: cf?.continent || 'unknown',
    city: cf?.city || 'unknown',
    colo: cf?.colo || 'unknown',
    timezone: cf?.timezone || 'UTC',
  };
}

/**
 * Check if the request is from a specific region
 */
export function isFromRegion(request: Request, regions: string[]): boolean {
  const cf = request.cf as CfProperties | undefined;
  if (!cf?.country) return false;
  
  return regions.includes(cf.country);
}

/**
 * Get latency estimate to different origins based on geo
 * (These are rough estimates for routing decisions)
 */
export function estimateLatency(request: Request): {
  us: number;
  eu: number;
  ap: number;
  recommended: 'us' | 'eu' | 'ap';
} {
  const cf = request.cf as CfProperties | undefined;
  const continent = cf?.continent || 'NA';

  // Rough latency estimates in ms based on continent
  const latencyMap: Record<string, { us: number; eu: number; ap: number }> = {
    'NA': { us: 20, eu: 100, ap: 150 },
    'SA': { us: 80, eu: 150, ap: 200 },
    'EU': { us: 100, eu: 20, ap: 180 },
    'AF': { us: 150, eu: 80, ap: 200 },
    'AS': { us: 180, eu: 150, ap: 50 },
    'OC': { us: 150, eu: 200, ap: 80 },
    'AN': { us: 200, eu: 200, ap: 200 },
  };

  const estimates = latencyMap[continent] || latencyMap['NA'];
  
  // Determine recommended region
  let recommended: 'us' | 'eu' | 'ap' = 'us';
  let minLatency = estimates.us;
  
  if (estimates.eu < minLatency) {
    minLatency = estimates.eu;
    recommended = 'eu';
  }
  if (estimates.ap < minLatency) {
    recommended = 'ap';
  }

  return {
    ...estimates,
    recommended,
  };
}

/**
 * EU data residency check (for GDPR compliance)
 */
export const EU_COUNTRIES = new Set([
  'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
  'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
  'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE',
  // EEA countries
  'IS', 'LI', 'NO',
]);

export function requiresEUDataResidency(request: Request): boolean {
  const cf = request.cf as CfProperties | undefined;
  if (!cf?.country) return false;
  
  return EU_COUNTRIES.has(cf.country);
}
