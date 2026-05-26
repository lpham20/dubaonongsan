import type { CropType } from "./api";

export const ALL_CROP_OPTION = "" as const;

export const MARKET_CROP_OPTIONS: { value: CropType | typeof ALL_CROP_OPTION }[] = [
  { value: ALL_CROP_OPTION },
  { value: "sau_rieng" },
  { value: "ca_phe" },
  { value: "ho_tieu" },
  { value: "lua" }
];

export const ROI_CROP_OPTIONS: { value: CropType; defaultYield: number; defaultPrice: number }[] = [
  { value: "ca_phe", defaultYield: 3.5, defaultPrice: 95_000 },
  { value: "sau_rieng", defaultYield: 18, defaultPrice: 72_000 },
  { value: "ho_tieu", defaultYield: 2.6, defaultPrice: 135_000 },
  { value: "lua", defaultYield: 6.5, defaultPrice: 8_500 }
];
