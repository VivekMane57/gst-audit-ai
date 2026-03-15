import { SignUp } from "@clerk/nextjs";

export default function SignupPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 to-blue-700 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">GST Audit AI</h1>
          <p className="text-blue-200 mt-2">Free mein shuru karo — 3 audits/month</p>
        </div>
        <SignUp />
      </div>
    </div>
  );
}