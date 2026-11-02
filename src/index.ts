import type {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { IThemeManager } from '@jupyterlab/apputils';

/**
 * Stylesheet shared by every variant, relative to the themes endpoint.
 */
const THEME_STYLE = 'jupyterlab_ipe_midnight_theme/index.css';

/**
 * The themes offered to the user, one per palette of the Neovim colorscheme.
 *
 * `variant` selects the palette through `data-ipe-variant` on the root element.
 * The name is what JupyterLab stores in settings, so changing it resets users.
 */
const VARIANTS = [
  { name: 'Ipe Midnight', variant: 'default' },
  { name: 'Ipe Midnight Soft', variant: 'soft' },
  { name: 'Ipe Midnight Cold', variant: 'cold' }
] as const;

/**
 * Register the Ipe Midnight themes.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab_ipe_midnight_theme:plugin',
  description: 'Adds the Ipe Midnight, Soft and Cold dark themes.',
  autoStart: true,
  requires: [IThemeManager],
  activate: (app: JupyterFrontEnd, manager: IThemeManager) => {
    const root = document.documentElement;

    for (const { name, variant } of VARIANTS) {
      manager.register({
        name,
        isLight: false,
        themeScrollbars: true,
        load: () => {
          root.dataset.ipeVariant = variant;
          return manager.loadCSS(THEME_STYLE);
        },
        unload: () => {
          // The theme manager unloads the old theme before loading the new one,
          // but only clear what this variant set, in case that order changes.
          if (root.dataset.ipeVariant === variant) {
            delete root.dataset.ipeVariant;
          }
          return Promise.resolve();
        }
      });
    }
  }
};

export default plugin;
