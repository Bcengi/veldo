/**
 * Veldo's adapter for Nuxt UI's runtime color plugin (runtime/plugins/colors.js), which vite.config.ts routes
 * here. The original builds the color variables at run time and writes them into a <style> element through
 * unhead, also when automatic color mode is off; the API's content security policy refuses that element. Veldo
 * compiles the same variables (--ui-primary, --ui-color-neutral-*, --ui-bg and the rest) into
 * src/styles/theme.css from its own palette, so this plugin installs nothing. Same shape: a Vue plugin.
 */
export default {
  install() {
    /* The theme variables are compiled CSS (src/styles/theme.css); nothing is written at run time. */
  },
}
