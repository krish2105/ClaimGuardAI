// Validated palette (see dataviz skill references/palette.md). Status colors
// are reserved for decision states; categorical slots are used in fixed
// order for plan-type identity; a single hue ramp is used for the
// (unranked) coding-flag magnitude bar.
export const STATUS_COLORS = {
  light: { good: "#0ca30c", warning: "#fab219", critical: "#d03b3b" },
  dark: { good: "#0ca30c", warning: "#fab219", critical: "#d03b3b" },
};

export const CATEGORICAL = {
  light: ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"],
  dark: ["#3987e5", "#199e70", "#c98500", "#008300", "#9085e9", "#e66767", "#d55181", "#d95926"],
};

export const SEQUENTIAL_BLUE = {
  light: ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"],
  dark: ["#b7d3f6", "#6da7ec", "#3987e5", "#1c5cab", "#0d366b"],
};

export const CHART_CHROME = {
  light: { grid: "#e1e0d9", axis: "#c3c2b7", mutedText: "#898781" },
  dark: { grid: "#2c2c2a", axis: "#383835", mutedText: "#898781" },
};
