import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
import { useNavigate } from "react-router"

export function ProfileView() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate("/login")
  }

  const displayName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.email?.split("@")[0] ??
    "ユーザー"

  const avatarUrl = user?.user_metadata?.avatar_url

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>プロフィール</CardTitle>
          <CardDescription>アカウント情報と設定の管理</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
          <Avatar className="h-24 w-24 border">
            {avatarUrl && <AvatarImage src={avatarUrl} alt={displayName} />}
            <AvatarFallback>
              {displayName.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-1">
            <h3 className="text-lg font-semibold">{displayName}</h3>
            <p className="text-sm text-muted-foreground">
              {user?.email ?? ""}
            </p>
          </div>
        </CardContent>
        <CardFooter className="flex justify-start">
          <Button variant="outline" className="gap-2" onClick={handleSignOut}>
            <IconLogout className="h-4 w-4" />
            ログアウト
          </Button>
        </CardFooter>
      </Card>

      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive">危険な操作</CardTitle>
          <CardDescription>
            アカウントの削除は元に戻せません。すべてのデータが失われます。
          </CardDescription>
        </CardHeader>
        <CardFooter>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" className="gap-2">
                <IconTrash className="h-4 w-4" />
                アカウントを削除
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>本当に削除しますか？</AlertDialogTitle>
                <AlertDialogDescription>
                  この操作は取り消せません。設定と登録科目のデータが完全に削除されます。
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>キャンセル</AlertDialogCancel>
                <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                  削除する
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardFooter>
      </Card>
    </div>
  )
}
