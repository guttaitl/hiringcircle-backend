import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });

import fs from "fs";
import path from "path";
import crypto from "crypto";
import mammoth from "mammoth";
import { Pool } from "pg";
import { randomUUID } from "crypto";

/* =========================
   CONFIG
   ========================= */
const RESUMES_DIR = path.join(process.cwd(), "uploads", "resumes");

const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  database: process.env.DB_NAME,
  ssl: false,
});

/* =========================
   HELPERS
   ========================= */
function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function parseDocx(filePath) {
  const buffer = fs.readFileSync(filePath);

  const htmlResult = await mammoth.convertToHtml({ buffer });
  const html = htmlResult.value || "";

  const textResult = await mammoth.extractRawText({ buffer });
  const text = textResult.value || "";

  return { html, text };
}

function kb(size) {
  return Math.max(1, Math.round(size / 1024));
}

/* =========================
   MAIN PROCESS
   ========================= */
async function run() {
  console.log("🔄 Starting resume reprocessing + insert...");

  const client = await pool.connect();

  try {
    const files = fs
      .readdirSync(RESUMES_DIR)
      .filter((f) => f.toLowerCase().endsWith(".docx"));

    console.log(`📄 Found ${files.length} resumes`);

    for (const file of files) {
      const filePath = path.join(RESUMES_DIR, file);
      const buffer = fs.readFileSync(filePath);
      const hash = sha256(buffer);

      const { html, text } = await parseDocx(filePath);

      const parsedSuccessfully = Boolean(html || text);
      const confidence =
        html.length > 1000 ? 0.95 :
        text.length > 1000 ? 0.75 :
        0.4;

      /* =========================
         1️⃣ TRY UPDATE
         ========================= */
      const updateRes = await client.query(
        `
        UPDATE candidate_resumes
        SET
          resume_text = $1,
          formatted_html = $2,
          parsed_successfully = $3,
          parsing_confidence_score = $4,
          last_parsed_at = NOW(),
          parser_version = 'v2-reprocess'
        WHERE resume_hash = $5
        `,
        [
          text,
          html,
          parsedSuccessfully,
          confidence,
          hash,
        ]
      );

      if (updateRes.rowCount > 0) {
        console.log(`✅ Reprocessed: ${file}`);
        continue;
      }

      /* =========================
         2️⃣ INSERT (MISSING ROW)
         ========================= */
      await client.query(
        `
        INSERT INTO candidate_resumes (
          id,
          source_type,
          original_file_name,
          file_path,
          file_type,
          mime_type,
          file_size_kb,
          resume_hash,
          resume_text,
          formatted_html,
          parsed_successfully,
          parsing_confidence_score,
          last_parsed_at,
          parser_version,
          is_active,
          is_deleted
        )
        VALUES (
          $1, 'import',
          $2, $3,
          'docx',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          $4,
          $5,
          $6,
          $7,
          $8,
          $9,
          NOW(),
          'v2-insert',
          true,
          false
        )
        ON CONFLICT (resume_hash) DO NOTHING
        `,
        [
          randomUUID(),
          file,
          filePath,
          kb(buffer.length),
          hash,
          text,
          html,
          parsedSuccessfully,
          confidence,
        ]
      );

      console.log(`➕ Inserted + processed: ${file}`);
    }

    console.log("🎉 Resume refresh complete");
  } catch (err) {
    console.error("❌ Reprocess failed:", err);
  } finally {
    client.release();
    process.exit(0);
  }
}

run();



