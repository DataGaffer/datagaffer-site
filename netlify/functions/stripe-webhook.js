// netlify/functions/stripe-webhook.js
exports.config = { rawBody: true };

const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  console.log("⚡ Incoming webhook event");
  const sig = event.headers["stripe-signature"];
  let stripeEvent;

  try {
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("❌ Stripe signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("✅ Webhook verified:", stripeEvent.type);

  // Handle subscription creation / update
  if (
    stripeEvent.type === "checkout.session.completed" ||
    stripeEvent.type === "customer.subscription.created" ||
    stripeEvent.type === "customer.subscription.updated"
  ) {
    const session = stripeEvent.data.object;
    const email = (session.customer_email || session.customer_details?.email || "").toLowerCase();
    const customerId = session.customer;

    let planCode = null;
    const priceId =
      session?.items?.data?.[0]?.price?.id ||
      session?.plan?.id ||
      session?.lines?.data?.[0]?.price?.id;

    if (priceId === process.env.STRIPE_PRICE_ID) planCode = "20_old";
    else if (priceId === process.env.STRIPE_PRICE_ID_20_NEW) planCode = "20_new";
    else if (priceId === process.env.STRIPE_PRICE_ID_50) planCode = "50";
    else if (priceId === process.env.STRIPE_PRICE_ID_250) planCode = "250";

    console.log("💳 Subscription active:", { email, customerId, planCode });

    if (email && planCode) {
      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: true,
          customer_id: customerId,
          plan: planCode,
        })
        .eq("email", email);

      if (error) console.error("❌ Supabase update failed:", error);
      else console.log(`✅ Subscription activated for ${email}`);
    }
  }

  // Handle subscription cancellation
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customerId = subscription.customer;
    const customer = await stripe.customers.retrieve(customerId);
    const email = (customer.email || "").toLowerCase();

    if (!email) {
      console.warn("⚠️ No email found for canceled subscription:", customerId);
      return { statusCode: 200, body: "no email found" };
    }

    console.log("⚠️ Subscription canceled:", { email, customerId });

    const { error } = await supabase
      .from("profiles")
      .update({
        is_subscribed: false,
        customer_id: null,
        plan: null,
      })
      .eq("email", email);

    if (error) console.error("❌ Supabase update failed:", error);
    else console.log(`✅ Subscription canceled for ${email}`);
  }

  return { statusCode: 200, body: "success" };
};




