import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import jwt from "jsonwebtoken";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 4000;
const JWT_SECRET = process.env.JWT_SECRET;
const DASHBOARD_PASSWORD = process.env.DASHBOARD_PASSWORD;



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


// 🔹 Só abre porta quando NÃO estiver na Vercel
if (!process.env.VERCEL) {
  app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
  });
}

// 🔹 Exporta o app para a Vercel usar
export default app;
