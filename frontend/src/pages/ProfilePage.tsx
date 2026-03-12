import { ProfileView } from "@/components/auth/ProfileView"

export function ProfilePage() {
  return (
    <div className="flex flex-col h-full bg-background md:-mt-6 md:-mx-6 md:p-6 lg:p-0">
      <div className="flex-1 lg:p-6 lg:pl-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight">プロフィール</h1>
        </div>
        <ProfileView />
      </div>
    </div>
  )
}
