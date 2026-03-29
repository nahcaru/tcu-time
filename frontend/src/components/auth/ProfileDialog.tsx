import { useState } from "react"
import { FunctionsHttpError } from "@supabase/supabase-js"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { IconLogout, IconTrash, IconSettings } from "@tabler/icons-react"
import { useNavigate } from "react-router"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useAuth } from "@/hooks/use-auth"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { supabase } from "@/lib/supabase"

interface ProfileDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

async function getDeleteErrorMessage(error: unknown): Promise<string> {
  if (error instanceof FunctionsHttpError) {
    try {
      const body = await error.context.json()
      if (body?.error === "unauthorized") return "認証エラーです。再ログインしてください。"
      if (body?.error === "delete_failed") return "アカウント削除に失敗しました。"
      if (body?.error === "server_error") return "サーバーエラーが発生しました。"
    } catch {
      return "アカウント削除に失敗しました。"
    }
  }

  if (error instanceof Error) return error.message
  return "アカウント削除に失敗しました。"
}

export function ProfileDialog({ open, onOpenChange }: ProfileDialogProps) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleSignOut = async () => {
    await signOut()
    onOpenChange(false) // Close modal on signout
  }

  const handleAdminNavigate = () => {
    onOpenChange(false)
    navigate("/admin")
  }

  const handleDeleteAccount = async () => {
    if (!user || deleteLoading) return

    setDeleteLoading(true)
    setDeleteError(null)

    const { error } = await supabase.functions.invoke("delete-account")

    if (error) {
      setDeleteError(await getDeleteErrorMessage(error))
      setDeleteLoading(false)
      return
    }

    await signOut()
    onOpenChange(false)
    navigate("/")
    setDeleteLoading(false)
  }

  const displayName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.email?.split("@")[0] ??
    "ユーザー"

  const avatarUrl = user?.user_metadata?.avatar_url
  const isAdmin = user?.app_metadata?.role === "admin"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>プロフィール</DialogTitle>
          <DialogDescription>アカウント情報と設定の管理</DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 py-4">
          {/* ユーザー情報セクション */}
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16 border">
              {avatarUrl && <AvatarImage src={avatarUrl} alt={displayName} />}
              <AvatarFallback className="text-lg">
                {displayName.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="space-y-0.5">
              <h3 className="text-base font-semibold">{displayName}</h3>
              <p className="max-w-[240px] overflow-hidden text-sm text-ellipsis whitespace-nowrap text-muted-foreground">
                {user?.email ?? ""}
              </p>
            </div>
          </div>

          {/* ログアウト・管理画面アクション */}
          <div className="flex justify-start gap-3">
            {isAdmin && (
              <Button
                variant="outline"
                size="sm"
                className="h-9 gap-1.5 text-sm"
                onClick={handleAdminNavigate}
              >
                <IconSettings className="h-4 w-4" />
                管理画面
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-9 gap-1.5 text-sm"
              onClick={handleSignOut}
            >
              <IconLogout className="h-4 w-4" />
              ログアウト
            </Button>
          </div>

          <div className="my-1 border-t" />

          {/* 危険な操作セクション */}
          <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
            <div className="space-y-1">
              <h4 className="flex items-center gap-1.5 text-sm font-semibold text-destructive">
                危険な操作
              </h4>
              <p className="text-xs leading-relaxed text-muted-foreground">
                アカウントの削除は元に戻せません。登録した時間割などのデータが完全に消去されます。
              </p>
            </div>
            <div className="mt-3">
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="h-8 gap-1.5"
                  >
                    <IconTrash className="h-3.5 w-3.5" />
                    アカウントを削除
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent className="max-w-[340px] sm:max-w-[425px]">
                  <AlertDialogHeader>
                    <AlertDialogTitle>本当に削除しますか？</AlertDialogTitle>
                    <AlertDialogDescription>
                      この操作は取り消せません。設定と登録科目のデータが完全に削除されます。
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter className="gap-2 sm:gap-0">
                    <AlertDialogCancel size="sm">キャンセル</AlertDialogCancel>
                    <AlertDialogAction
                      className="text-destructive-foreground h-9 bg-destructive text-sm hover:bg-destructive/90"
                      onClick={(event) => {
                        event.preventDefault()
                        void handleDeleteAccount()
                      }}
                    >
                      {deleteLoading ? "削除中..." : "削除する"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              {deleteError && (
                <p className="mt-2 text-xs text-destructive">{deleteError}</p>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
