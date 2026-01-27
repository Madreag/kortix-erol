/**
 * Speculation Rules Component
 * 
 * Enables browser-native prefetching and prerendering via Speculation Rules API.
 * This allows instant navigation by specifying which pages to prefetch/prerender.
 * 
 * @see https://developer.chrome.com/docs/web-platform/speculation-rules
 */

export function SpeculationRules() {
  const rules = {
    prerender: [
      {
        where: { href_matches: '/projects/*/thread/*' },
        eagerness: 'moderate', // On hover (200ms delay)
      },
    ],
    prefetch: [
      {
        where: { href_matches: '/dashboard' },
        eagerness: 'eager', // As soon as possible
      },
      {
        where: { href_matches: '/projects/*' },
        eagerness: 'moderate', // On hover
      },
      {
        where: { selector_matches: '.prefetch-link' },
        eagerness: 'moderate',
      },
      {
        where: { href_matches: '/settings/*' },
        eagerness: 'conservative', // On mouse down
      },
    ],
  };

  return (
    <script
      type="speculationrules"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(rules),
      }}
    />
  );
}
