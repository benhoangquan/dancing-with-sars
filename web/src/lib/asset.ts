// Asset URLs. A sub-path host sets NEXT_PUBLIC_BASE_PATH ("/dancing-with-sars"); manifest AssetPaths are
// relative to public/, so every file URL goes through here.
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Site-relative URL for a manifest AssetPath, for example "/dancing-with-sars/data/rondonia/sar_after.tif". */
export const assetUrl = (path: string) => `${BASE_PATH}/${path}`;

/** Absolute URL, which the cog:// protocol needs. Browser only. */
export const absoluteAssetUrl = (path: string) => new URL(assetUrl(path), window.location.origin).href;
