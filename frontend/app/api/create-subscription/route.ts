// FILE: app/api/create-subscription/route.ts
// Razorpay subscription create karta hai

import { NextRequest, NextResponse } from "next/server";
import Razorpay from "razorpay";

const razorpay = new Razorpay({
  key_id:     process.env.RAZORPAY_KEY_ID!,
  key_secret: process.env.RAZORPAY_KEY_SECRET!,
});

export async function POST(req: NextRequest) {
  try {
    const { plan_id, user_id, email, name } = await req.json();

    if (!plan_id) {
      return NextResponse.json({ error: "plan_id required" }, { status: 400 });
    }

    // Razorpay subscription create
    const subscription = await (razorpay.subscriptions as any).create({
      plan_id:        plan_id,
      customer_notify: 1,
      quantity:        1,
      total_count:     12,          // 12 months (yearly cycle)
      notes: {
        user_id: user_id || "",
        email:   email   || "",
        name:    name    || "",
      },
    });

    return NextResponse.json({
      subscription_id: subscription.id,
      status:          subscription.status,
    });

  } catch (err: any) {
    console.error("Razorpay subscription error:", err);
    return NextResponse.json(
      { error: err?.error?.description || "Subscription create failed" },
      { status: 500 }
    );
  }
}