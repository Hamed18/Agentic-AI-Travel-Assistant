import React, { useState } from "react";
import { loginUser, registerUser, createGuestSession } from "../api";
import { X, Lock, Mail, User, Shield, Sparkles, AlertCircle, Loader2 } from "lucide-react";

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("user"); // "user" | "admin"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "login") {
        const res = await loginUser({ email, password });
        onAuthSuccess(res.user);
        onClose();
      } else {
        const res = await registerUser({ email, password, name, role });
        onAuthSuccess(res.user);
        onClose();
      }
    } catch (err) {
      setError(err.message || "Authentication failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await createGuestSession();
      onAuthSuccess(res.user);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to start guest session.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 text-slate-100">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 mb-3">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight">
            {mode === "login" ? "Welcome Back" : "Create Traveler Account"}
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            {mode === "login"
              ? "Sign in to access your saved trips and documents."
              : "Register to keep your travel itineraries and episodic history."}
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="grid grid-cols-2 p-1 bg-slate-950/60 rounded-xl mb-6 border border-slate-800/80">
          <button
            type="button"
            onClick={() => {
              setMode("login");
              setError("");
            }}
            className={`py-2 text-sm font-medium rounded-lg transition-all ${
              mode === "login"
                ? "bg-blue-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("register");
              setError("");
            }}
            className={`py-2 text-sm font-medium rounded-lg transition-all ${
              mode === "register"
                ? "bg-blue-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Register
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="flex items-center gap-2 p-3 mb-4 text-sm text-red-300 bg-red-950/50 border border-red-800/50 rounded-xl">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  required
                  placeholder="Alex Traveler"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-9 pr-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
              <input
                type="email"
                required
                placeholder="you@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
              <input
                type="password"
                required
                minLength={6}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
              />
            </div>
          </div>

          {mode === "register" && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Account Role
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRole("user")}
                  className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl border text-xs font-medium transition ${
                    role === "user"
                      ? "bg-blue-600/20 border-blue-500 text-blue-300"
                      : "bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <User className="w-3.5 h-3.5" />
                  Traveler
                </button>
                <button
                  type="button"
                  onClick={() => setRole("admin")}
                  className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl border text-xs font-medium transition ${
                    role === "admin"
                      ? "bg-purple-600/20 border-purple-500 text-purple-300"
                      : "bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <Shield className="w-3.5 h-3.5" />
                  Admin
                </button>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 font-semibold text-sm rounded-xl text-white shadow-lg shadow-blue-500/25 transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : mode === "login" ? (
              "Sign In"
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-800"></div>
          </div>
          <span className="relative px-3 bg-slate-900 text-xs text-slate-500 uppercase tracking-wider">
            or continue without account
          </span>
        </div>

        {/* Continue as Guest */}
        <button
          type="button"
          onClick={handleGuest}
          disabled={loading}
          className="w-full py-2.5 px-4 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 font-medium text-sm rounded-xl transition flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4 text-amber-400" />
          Continue as Guest (2-hr temporary session)
        </button>
      </div>
    </div>
  );
}
