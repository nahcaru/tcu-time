import { useState } from "react"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"

type AuthView = "sign_in" | "sign_up" | "forgotten_password"

export function LoginForm() {
  const [view, setView] = useState<AuthView>("sign_in")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null)

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setMessage(null)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (error) {
      setMessage({ type: "error", text: error.message })
    }
  }

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setMessage(null)
    const { error } = await supabase.auth.signUp({ email, password })
    setLoading(false)
    if (error) {
      setMessage({ type: "error", text: error.message })
    } else {
      setMessage({ type: "success", text: "確認メールを送信しました。メールを確認してください。" })
    }
  }

  async function handleForgotPassword(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setMessage(null)
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/profile`,
    })
    setLoading(false)
    if (error) {
      setMessage({ type: "error", text: error.message })
    } else {
      setMessage({ type: "success", text: "パスワード再設定のメールを送信しました。" })
    }
  }

  async function handleGoogleSignIn() {
    setLoading(true)
    setMessage(null)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/` },
    })
    if (error) {
      setLoading(false)
      setMessage({ type: "error", text: error.message })
    }
  }

  const titles: Record<AuthView, string> = {
    sign_in: "ログイン",
    sign_up: "アカウント登録",
    forgotten_password: "パスワード再設定",
  }

  return (
    <div className="w-full max-w-sm mx-auto p-6 bg-card rounded-xl border shadow-sm">
      <div className="mb-6 text-center">
        <h2 className="text-2xl font-bold">{titles[view]}</h2>
        <p className="text-sm text-muted-foreground mt-1">TCU-TIMEへようこそ</p>
      </div>

      {view !== "forgotten_password" && (
        <>
          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={handleGoogleSignIn}
            disabled={loading}
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Google で{view === "sign_in" ? "ログイン" : "登録"}
          </Button>

          <div className="relative my-6">
            <Separator />
            <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-xs text-muted-foreground">
              または
            </span>
          </div>
        </>
      )}

      <form
        onSubmit={
          view === "sign_in"
            ? handleSignIn
            : view === "sign_up"
              ? handleSignUp
              : handleForgotPassword
        }
        className="space-y-4"
      >
        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium">
            メールアドレス
          </label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>

        {view !== "forgotten_password" && (
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              パスワード
            </label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={view === "sign_in" ? "current-password" : "new-password"}
            />
          </div>
        )}

        {message && (
          <p
            className={`text-sm ${message.type === "error" ? "text-destructive" : "text-green-600 dark:text-green-400"}`}
          >
            {message.text}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading
            ? view === "sign_in"
              ? "ログイン中..."
              : view === "sign_up"
                ? "登録中..."
                : "送信中..."
            : view === "sign_in"
              ? "ログイン"
              : view === "sign_up"
                ? "登録"
                : "再設定メールを送信"}
        </Button>
      </form>

      <div className="mt-4 text-center text-sm space-y-1">
        {view === "sign_in" && (
          <>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground underline-offset-4 hover:underline block w-full"
              onClick={() => { setView("forgotten_password"); setMessage(null) }}
            >
              パスワードをお忘れですか？
            </button>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground underline-offset-4 hover:underline block w-full"
              onClick={() => { setView("sign_up"); setMessage(null) }}
            >
              アカウントをお持ちでないですか？登録
            </button>
          </>
        )}
        {view === "sign_up" && (
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground underline-offset-4 hover:underline block w-full"
            onClick={() => { setView("sign_in"); setMessage(null) }}
          >
            アカウントをお持ちですか？ログイン
          </button>
        )}
        {view === "forgotten_password" && (
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground underline-offset-4 hover:underline block w-full"
            onClick={() => { setView("sign_in"); setMessage(null) }}
          >
            ログインに戻る
          </button>
        )}
      </div>
    </div>
  )
}
