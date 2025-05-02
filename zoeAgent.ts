/**********************************************************************
 * Zoe – optimized agent (April 2025, bug-fixed)
 *********************************************************************/
import path from "path";
import { readFile } from "fs/promises";
import { Pinecone } from "@pinecone-database/pinecone";
import { PineconeStore } from "@langchain/pinecone";
import { OpenAIEmbeddings } from "@langchain/openai";
import { CustomChatOpenAI } from "./langchain/customTokenEstimator";

import {
  AIMessage,
  HumanMessage,
  SystemMessage,
  BaseMessage,
} from "@langchain/core/messages";
import {
  ChatPromptTemplate,
  MessagesPlaceholder,
} from "@langchain/core/prompts";
import { createHistoryAwareRetriever } from "langchain/chains/history_aware_retriever";
import { formatDocumentsAsString } from "langchain/util/document";
import { DynamicStructuredTool } from "langchain/tools";
import { AgentExecutor, createToolCallingAgent } from "langchain/agents";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { z } from "zod";

import { logHoneypotHit, getHitCount } from "./db/honeypot";
import {
  sanitizeOutput,
  validateUserInput,
} from "./security/validation";
import logger from "./logger";
import { loadRemixPrompt } from "./prompts/remixPrompt";
import { encode } from "gpt-tokenizer"; // tiny pkg – 0-dep

/*───────────────────────────────────────────────────────────*/
/* Globals & tiny caches                                     */
/*───────────────────────────────────────────────────────────*/
const promptCache = new Map<string, string>();
const faqCache = new Map<string, string>(); // 1-hour TTL
const FAQ_TTL_MS = 60 * 60 * 1_000;

const cacheSet = (k: string, v: string) => {
  faqCache.set(k, v);
  setTimeout(() => faqCache.delete(k), FAQ_TTL_MS).unref();
};

/*───────────────────────────────────────────────────────────*/
/* Prompt loader                                             */
/*───────────────────────────────────────────────────────────*/
async function loadPrompt(lang: string, mode: "system" | "lite") {
  const locale = lang.toLowerCase().startsWith("ja") ? "jp" : "en";
  const key = `${locale}:${mode}`;
  if (promptCache.has(key)) return promptCache.get(key)!;
  const p = path.resolve(
    process.cwd(),
    "src",
    "lib",
    "prompts",
    locale,
    `${mode}.md`
  );
  const md = await readFile(p, "utf8");
  promptCache.set(key, md);
  return md;
}

/*───────────────────────────────────────────────────────────*/
/* Trimmed chat-history window (≈token-budget 600)           */
/*───────────────────────────────────────────────────────────*/

/** fast-n-dirty token estimator (≈ 4 chars / token) */
const estTokens = (txt: string) => Math.ceil(txt.length / 4);

/**
 * Build the window we feed back to the agent.
 *  – keeps ONLY user / assistant turns
 *  – always prepends the lightweight `<REMIXED>` tag
 */
export function buildWindow(
  hist: { role: string; content: string }[],
  remixedTag = "<REMIXED>",
  budget = 600
): (HumanMessage | AIMessage | SystemMessage)[] {
  const window: (HumanMessage | AIMessage)[] = [];
  let used = estTokens(remixedTag); // cost of the tag itself

  // walk history newest → oldest
  for (let i = hist.length - 1; i >= 0 && used < budget; i--) {
    const m = hist[i];

    /* 🧹  NEW RULE: skip every *system* turn (they’re huge & redundant) */
    if (m.role === "system") continue;

    const cost = estTokens(m.content);
    if (used + cost > budget) break;

    used += cost;
    window.push(
      m.role === "user"
        ? new HumanMessage(m.content)
        : new AIMessage(m.content)
    );
  }

  // return in chronological order, plus the tag
  return [new SystemMessage(remixedTag), ...window.reverse()];
}

/*───────────────────────────────────────────────────────────*/
export async function getZoeAgent(language = "en") {
  /* 1️⃣  Embeddings */
  const openaiKey = process.env.OPENAI_API_KEY!;
  const openRouterKey = process.env.OPENROUTER_API_KEY!;

  const embeddings = new OpenAIEmbeddings({
    apiKey: openaiKey,
    model: "text-embedding-3-small",
  });

  /* 2️⃣  LLM handles */
  const llmFlash = new CustomChatOpenAI({
    modelName: "google/gemini-2.5-flash-preview",
    openAIApiKey: openRouterKey,
    configuration: { baseURL: "https://openrouter.ai/api/v1" },
    streaming: true,
    temperature: 0.3,
    verbose: false,
  });

  const llmPro = new CustomChatOpenAI({
    modelName: "google/gemini-2.5-pro-preview-03-25",
    openAIApiKey: openRouterKey,
    configuration: { baseURL: "https://openrouter.ai/api/v1" },
    streaming: true,
    temperature: 0.3,
    verbose: true,
  });

  /* 3️⃣  Pinecone vector store */
  const indexName = process.env.PINECONE_INDEX!;
  const pcStore = await (async () => {
    const pc = new Pinecone();
    const idx = pc.Index(indexName);
    const stats = await idx.describeIndexStats();
    return stats.totalRecordCount
      ? PineconeStore.fromExistingIndex(embeddings, { pineconeIndex: idx })
      : PineconeStore.fromDocuments([], embeddings, { pineconeIndex: idx });
  })();

  /* 4️⃣  Retrieval helper */
  const rephrasePrompt = ChatPromptTemplate.fromMessages([
    [
      "system",
      "Rewrite the last user question using the chat history. Return a standalone question in the same language.",
    ],
    ["placeholder", "{chat_history}"],
    ["human", "{input}"],
  ]);

  const histRetriever = await createHistoryAwareRetriever({
    llm: llmFlash,
    retriever: pcStore.asRetriever({ k: 10, searchType: "mmr" }),
    rephrasePrompt,
  });

  /*───────────────────────────────────────────────────────────*/
  /* Tools                                                    */
  /*───────────────────────────────────────────────────────────*/

  /** simple greeting */
  const GreetTool = new DynamicStructuredTool({
    name: "greet_user",
    description: "Return a short greeting.",
    schema: z.object({}),
    func: async () =>
      language.startsWith("jp")
        ? "こんにちは！ 👋 どのようなお仕事をお探しですか？"
        : "Hello! 👋 How can I help you with your job search today?",
  });

  /** FAQ */
  const STATIC_FAQ: Record<string, string> = {
    "remote-japan":
      "“Remote-Japan” means you can work from **anywhere inside Japan**; Zeal cannot support full-time employees living abroad right now.",
  };

  const FAQTool = new DynamicStructuredTool({
    name: "faq_lookup",
    description: "Answer policy / benefit questions.",
    schema: z.object({ query: z.string() }),
    func: async ({ query }) => {
      const key = query.toLowerCase().trim();
      if (STATIC_FAQ[key]) return STATIC_FAQ[key];
      const cached = faqCache.get(key);
      if (cached) return cached;

      const docs = await pcStore.similaritySearch(key, 2);
      const answer = docs.length
        ? formatDocumentsAsString(docs)
        : "FAQ_NOT_FOUND";
      cacheSet(key, answer);
      return answer;
    },
  });

  /** Job-search */
  const JobSearchTool = new DynamicStructuredTool({
    name: "job_search",
    description: "Search & rank Zeal job postings.",
    schema: z.object({
      query: z.string(),
      chat_history: z.array(z.custom<BaseMessage>()).optional(),
    }),
    func: async ({ query, chat_history }) => {
      /* 1️⃣  pull docs */
      const stats = await pcStore.pineconeIndex.describeIndexStats();
      const all =
        stats.totalRecordCount <= 25
          ? await pcStore.similaritySearch("", 25)
          : await histRetriever.invoke({ input: query, chat_history });

      /* 2️⃣  location clarification */
      if (!/(tokyo|remote)/i.test(query))
        return "Do you have a preferred location? Openings: Tokyo / Remote-Japan.";

      /* 3️⃣  no match */
      if (!all.length)
        return `Nothing matches that right now. Want me to ping you when something suitable appears?`;

      /* 4️⃣  compact list & ranking */
      const jobsList = all
        .slice(0, 20)
        .map(
          (d, i) =>
            `${i + 1}. ${d.metadata.title} | ${d.metadata.location}\n${d.pageContent.slice(
              0,
              140
            )}…`
        )
        .join("\n\n");

      const rankPrompt = ChatPromptTemplate.fromTemplate(
        `You are a helpful recruiter. **Do NOT output citations, IDs, or tool tags.**
Rank the jobs below for the user query: "{query}".
Return up to 3 markdown bullets, each with a 1-sentence reason.

---
{jobs}`
      );

      const llm = all.length <= 20 ? llmFlash : llmPro;
      const ranked = await llm.invoke(await rankPrompt.format({ query, jobs: jobsList }));

      return ranked.content;
    },
  });

  const tools = [GreetTool, FAQTool, JobSearchTool];

  /*───────────────────────────────────────────────────────────*/
  /* Prompts & agent                                           */
  /*───────────────────────────────────────────────────────────*/
  const fullSystem = await loadPrompt(language, "system");
  const remixTag = await loadRemixPrompt();

  const agent = createToolCallingAgent({
    llm: llmPro, // orchestration call only
    tools,
    prompt: ChatPromptTemplate.fromMessages([
      ["system", fullSystem],          // <— long rules (one-time)
      new MessagesPlaceholder("chat_history"),
      ["human", "{input}"],
      ["placeholder", "{agent_scratchpad}"],
    ]),
  });

  const executor = new AgentExecutor({ agent, tools });

  /*───────────────────────────────────────────────────────────*/
  /* Public API                                                */
  /*───────────────────────────────────────────────────────────*/
  return {
    async chat(
      message: string,
      history: { role: string; content: string }[],
      sessionId = "anon"
    ) {
      /* greet */
      if (/^(hi|hello|hey|yo|こんにちは)/i.test(message.trim()))
        return GreetTool.invoke({});

      /* security */
      if (!validateUserInput(message))
        return "⚠️ That doesn’t look safe. Could you rephrase?";
      if (/jailbreak|ignore.*system/i.test(message)) {
        logHoneypotHit(sessionId, message);
        if (getHitCount(sessionId) >= 3)
          return "🚫 Too many suspicious requests. Please try again later.";
      }

      /* trimmed history window */
      const chat_history = buildWindow(history, remixTag);

      const { output } = await executor.invoke({
        input: message,
        chat_history,
      });

      // scrub any accidental citation tags
      return sanitizeOutput(output.replace(/〔(?:\d+|tool_\d+)〕/g, "").trim());
    },
  };
}
