import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import OpenAI from "openai";

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

app.get("/api/health", (req, res) => {
  res.json({
    success: true,
    service: "MarketFlow API",
    status: "online"
  });
});

app.post("/api/campaigns/preview", (req, res) => {
  res.json({
    success: true,
    campaign: {
      ...req.body,
      status: "Draft",
      readyToReview: true
    }
  });
});

app.post("/api/ai/generate", async (req, res) => {
  const { prompt } = req.body;

  if (!prompt) {
    return res.status(400).json({
      success: false,
      error: "Prompt is required"
    });
  }

  if (!process.env.OPENAI_API_KEY) {
    return res.status(503).json({
      success: false,
      error: "OPENAI_API_KEY is not configured"
    });
  }

  try {
    const client = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });

    const response = await client.responses.create({
      model: "gpt-5.6-luna",
      instructions: `
You are the AI marketing strategist inside MarketFlow.

Create a practical marketing plan based on the user's request.

Include:
- campaign objective
- target audience
- recommended platform
- advertising angle
- ad copy
- CTA
- suggested budget split
- next actions

Keep the answer clear and useful.
      `,
      input: prompt
    });

    res.json({
      success: true,
      result: response.output_text
    });

  } catch (error) {
    console.error(error);

    res.status(500).json({
      success: false,
      error: "AI generation failed"
    });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, "0.0.0.0", () => {
  console.log(
    `MarketFlow API running on http://localhost:${PORT}`
  );
});
