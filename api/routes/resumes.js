import fs from "fs";
import path from "path";
import crypto from "crypto";
import multer from "multer";
import { v4 as uuidv4 } from "uuid";

import pool from "../db.js";

/* ------------------------------------------------------------------
   MULTER CONFIG
------------------------------------------------------------------ */

const upload = multer({
  limits: {
    fileSize: 5 * 1024 * 1024, // 5 MB
  },
  fileFilter(req, file, cb) {
    const allowedMimeTypes = [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ];

    if (!allowedMimeTypes.includes(file.mimetype)) {
      return cb(new Error("Unsupported file type"));
    }
    cb(null, true);
  },
});

/* ------------------------------------------------------------------
   ROUTE REGISTRATION
------------------------------------------------------------------ */

export function registerResumeRoutes(app) {
  /**
   * POST /api/resumes/upload
   *
   * Flow:
   * 1. Save file
   * 2. Insert resume (PENDING parse)
   * 3. Create submission linked to resume
   * 4. Python parser will process it
   */
  app.post(
    "/api/resumes/upload",
    upload.single("file"),
    async (req, res) => {
      const client = await pool.connect();

      try {
        const { user_id } = req.body;
        const file = req.file;

        if (!user_id) {
          return res.status(400).json({ error: "user_id is required" });
        }

        if (!file) {
          return res.status(400).json({ error: "Resume file is required" });
        }

        /* ------------------------------------------------------------
           PREPARE STORAGE
        ------------------------------------------------------------ */

        const resumeId = uuidv4();
        const submissionId = uuidv4();

        const extension = path.extname(file.originalname).toLowerCase();
        const userDir = path.join("api", "resumes", user_id);

        fs.mkdirSync(userDir, { recursive: true });

        const filePath = path.join(userDir, `${resumeId}${extension}`);
        fs.writeFileSync(filePath, file.buffer);

        /* ------------------------------------------------------------
           HASH (DEDUP / TRACEABILITY)
        ------------------------------------------------------------ */

        const resumeHash = crypto
          .createHash("sha256")
          .update(file.buffer)
          .digest("hex");

        /* ------------------------------------------------------------
           DB TRANSACTION
        ------------------------------------------------------------ */

        await client.query("BEGIN");

        /* ---------------- INSERT RESUME (PENDING PARSE) ------------ */

        await client.query(
          `
          INSERT INTO candidate_resumes (
            id,
            user_id,
            source_type,
            original_file_name,
            file_path,
            file_type,
            mime_type,
            file_size_kb,
            resume_hash,
            resume_text,
            parsed_successfully,
            is_primary
          )
          VALUES (
            $1,$2,'user',
            $3,$4,$5,$6,$7,$8,
            'Resume parsing pending',
            false,
            true
          )
        `,
          [
            resumeId,
            user_id,
            file.originalname,
            filePath,
            extension.replace(".", ""),
            file.mimetype,
            Math.ceil(file.size / 1024),
            resumeHash,
          ]
        );

        /* ---------------- CREATE SUBMISSION ---------------- */

        await client.query(
          `
          INSERT INTO submissions (
            submission_id,
            user_id,
            resume_id,
            status,
            created_at
          )
          VALUES ($1, $2, $3, 'PENDING', NOW())
        `,
          [submissionId, user_id, resumeId]
        );

        await client.query("COMMIT");

        /* ------------------------------------------------------------
           RESPONSE
        ------------------------------------------------------------ */

        return res.status(201).json({
          resume_id: resumeId,
          submission_id: submissionId,
          status: "uploaded",
          parsing: "queued",
        });

      } catch (err) {
        await client.query("ROLLBACK");
        console.error("❌ Resume upload failed:", err);
        return res.status(500).json({ error: "Resume upload failed" });

      } finally {
        client.release();
      }
    }
  );
}



