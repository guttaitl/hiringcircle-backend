import fs from "fs";
import path from "path";
import mammoth from "mammoth";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

/**
 * Extract plain text from resume file
 * Supported: PDF, DOCX
 */
export async function extractText(filePath) {
  try {
    const ext = path.extname(filePath).toLowerCase();

    // ===== PDF =====
    if (ext === ".pdf") {
      const data = new Uint8Array(fs.readFileSync(filePath));
      const pdf = await pdfjsLib.getDocument({ data }).promise;

      let text = "";
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        text += content.items.map(item => item.str).join(" ") + " ";
      }

      return normalizeText(text);
    }

    // ===== DOCX =====
    if (ext === ".docx") {
      const result = await mammoth.extractRawText({ path: filePath });
      return normalizeText(result.value);
    }

    throw new Error(`Unsupported file extension: ${ext}`);
  } catch (err) {
    console.error("❌ Text extraction failed:", err);
    throw err;
  }
}

function normalizeText(text) {
  return text
    ?.replace(/\r\n/g, "\n")
    .replace(/\n{2,}/g, "\n")
    .replace(/\s+/g, " ")
    .trim();
}



