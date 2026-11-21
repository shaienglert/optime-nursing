/**
 * Shrink a photo in the browser before upload.
 *
 * Phone photos are often 5–12MB, while the hosting proxy accepts request bodies of
 * only a few MB. The backend re-encodes to 1600px anyway, so sending ~2000px loses nothing.
 */
const MAX_EDGE = 2000;
const QUALITY = 0.88;

export async function shrinkImage(file: File): Promise<Blob> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    // Formats the browser cannot decode (e.g. HEIC on some browsers) go up as-is;
    // the backend then accepts or rejects them with a readable reason.
    return file;
  }
  const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return file;
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", QUALITY));
  return blob ?? file;
}
