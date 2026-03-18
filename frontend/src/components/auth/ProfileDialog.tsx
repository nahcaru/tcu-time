import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { IconLogout, IconTrash } from "@tabler/icons-react"
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

interface ProfileDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ProfileDialog({ open, onOpenChange }: ProfileDialogProps) {
  const { user, signOut } = useAuth()

  const handleSignOut = async () => {
    await signOut()
    onOpenChange(false) // Close modal on signout
  }

  const displayName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.email?.split("@")[0] ??
    "ユーザー"

  const avatarUrl = user?.user_metadata?.avatar_url

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

          {/* ログアウトアクション */}
          <div className="flex justify-start">
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
                    <AlertDialogAction className="text-destructive-foreground h-9 bg-destructive text-sm hover:bg-destructive/90">
                      削除する
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
