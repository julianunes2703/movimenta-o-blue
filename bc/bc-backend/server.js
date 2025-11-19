import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import jwt from "jsonwebtoken";
import fetch from "node-fetch";


dotenv.config();

const app = express();
const PORT = process.env.PORT || 4000;
const JWT_SECRET = process.env.JWT_SECRET;
const DASHBOARD_PASSWORD = process.env.DASHBOARD_PASSWORD;

// base do Apps Script (até o /exec)
const DRE_SCRIPT_BASE_URL = process.env.DRE_SCRIPT_BASE_URL;

// Middlewares básicos
app.use(cors());
app.use(express.json());

// Rota de teste
app.get("/", (req, res) => {
  res.send("API do dashboard rodando");
});

// --- LOGIN ---
// front manda { password: "..." }
app.post("/login", (req, res) => {
  const { password } = req.body;

  if (!password) {
    return res.status(400).json({ message: "Senha obrigatória" });
  }

  if (password !== DASHBOARD_PASSWORD) {
    return res.status(401).json({ message: "Senha inválida" });
  }

  const payload = { role: "dashboard-user" };
  const token = jwt.sign(payload, JWT_SECRET, { expiresIn: "8h" });

  res.json({ token });
});

// --- MIDDLEWARE DE AUTENTICAÇÃO ---
function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization; // "Bearer xxx"

  if (!authHeader) {
    return res.status(401).json({ message: "Token não fornecido" });
  }

  const [, token] = authHeader.split(" ");

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    return next();
  } catch (err) {
    return res.status(401).json({ message: "Token inválido ou expirado" });
  }
}

// --- NOVA ROTA PROTEGIDA PARA DRE (CSV via Apps Script) ---
app.get("/dre-csv", authMiddleware, async (req, res) => {
  try {
    const { sheetId, sheet = "DRE", range = "A1:Z999" } = req.query;

    if (!sheetId) {
      return res.status(400).json({ message: "sheetId é obrigatório" });
    }

    if (!DRE_SCRIPT_BASE_URL) {
      return res
        .status(500)
        .json({ message: "DRE_SCRIPT_BASE_URL não configurada no servidor" });
    }

    const url =
      `${DRE_SCRIPT_BASE_URL}` +
      `?id=${encodeURIComponent(sheetId)}` +
      `&sheet=${encodeURIComponent(sheet)}` +
      `&range=${encodeURIComponent(range)}`;

    
    console.log("[/dre-csv] URL chamada:", url);
    const response = await fetch(url);

     

  if (!response.ok) {
  const txt = await response.text().catch(() => "");
  console.error("Erro Apps Script:", response.status, txt);

  // devolver pro front o erro real do Apps Script
  return res
    .status(response.status)
    .send(txt || "Erro ao buscar DRE (Apps Script)");
}



    const text = await response.text();
    res.type("text/csv").send(text);
  } catch (err) {
    console.error("Erro lendo DRE:", err);
    res.status(500).json({ message: "Erro interno ao buscar DRE" });
  }
});

// 🔹 Só abre porta quando NÃO estiver na Vercel
if (!process.env.VERCEL) {
  app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
  });
}

// 🔹 Exporta o app para a Vercel usar
export default app;
