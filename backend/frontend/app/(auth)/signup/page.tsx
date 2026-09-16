import { redirect } from "next/navigation";

export default function SignUpPage({
  searchParams,
}: {
  searchParams: { [key: string]: string | string[] | undefined };
}) {
  const redirectParam =
    typeof searchParams?.redirect === "string" ? searchParams.redirect : null;
  const target = redirectParam
    ? `/register?redirect=${encodeURIComponent(redirectParam)}`
    : "/register";
  redirect(target);
}
