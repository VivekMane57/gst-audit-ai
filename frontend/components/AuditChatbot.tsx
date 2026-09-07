"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { askAuditAgent } from "@/lib/agentApi";

interface Message {
  role: "user" | "assistant";
  content: string;
  steps?: number;
}

export default function AuditChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "**Hello! I am AuditAI's Principal CA Assistant.**\n\nAsk me to verify supplier trust scores, look up statutory HSN tax slabs, or explain compliance discrepancies under the CGST Act.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setLoading(true);

    try {
      const data = await askAuditAgent(userText);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          steps: data.steps_taken,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "**Error:** Unable to connect to the GST Agent backend engine.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans">
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 px-5 py-3 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-xl hover:shadow-2xl transition duration-200"
        >
          <span className="text-xl">🤖</span>
          <span className="font-semibold text-sm">Ask Audit AI</span>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="w-[420px] md:w-[480px] h-[580px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-slate-900 text-white p-4 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <div>
                <h3 className="font-semibold text-sm">AuditAI Assistant</h3>
                <p className="text-[11px] text-emerald-400">Online • GST Statutory Copilot</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-slate-400 hover:text-white text-lg px-2"
              aria-label="Close Chat"
            >
              ✕
            </button>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-50 text-sm">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[92%] p-3.5 rounded-2xl ${
                    m.role === "user"
                      ? "bg-blue-600 text-white rounded-br-none"
                      : "bg-white text-slate-800 border border-gray-200 rounded-bl-none shadow-sm"
                  }`}
                >
                  {m.role === "user" ? (
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  ) : (
                    <div className="prose prose-sm max-w-none text-slate-800 space-y-2">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          table: ({ node, ...props }) => (
                            <table
                              className="w-full text-xs border-collapse border border-gray-300 my-2 rounded-lg overflow-hidden"
                              {...props}
                            />
                          ),
                          th: ({ node, ...props }) => (
                            <th
                              className="border border-gray-300 bg-slate-100 px-2.5 py-1.5 text-left font-semibold text-slate-900"
                              {...props}
                            />
                          ),
                          td: ({ node, ...props }) => (
                            <td className="border border-gray-300 px-2.5 py-1.5 text-slate-700" {...props} />
                          ),
                          strong: ({ node, ...props }) => (
                            <strong className="font-bold text-slate-950" {...props} />
                          ),
                          ul: ({ node, ...props }) => (
                            <ul className="list-disc pl-4 space-y-1 my-1" {...props} />
                          ),
                          ol: ({ node, ...props }) => (
                            <ol className="list-decimal pl-4 space-y-1 my-1" {...props} />
                          ),
                        }}
                      >
                        {m.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
                {m.steps && (
                  <span className="text-[10px] text-gray-400 mt-1 px-1">
                    ⚡ {m.steps} tool executions
                  </span>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-gray-500 text-xs p-2">
                <span className="animate-spin text-sm">⏳</span> Synthesizing audit findings & legal sections...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Input Form */}
          <form onSubmit={handleSend} className="p-3 bg-white border-t border-gray-200 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about supplier risk, HSN code, or compliance..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}