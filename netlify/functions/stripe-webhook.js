// netlify/functions/stripe-webhook.js
const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // ⚠️ must be service role key, NOT anon
);

exports.handler = async (event) => {
  const sig = event.headers["stripe-signature"];
  let stripeEvent;

  try {
    // Verify webhook signature
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("⚠️ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  // ✅ Handle checkout session completed
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;

    // Get customer email
    const email = session.customer_email || session.customer_details?.email;
    if (!email) {
      console.error("⚠️ No email found in session");
      return { statusCode: 400, body: "No email found" };
    }

    // Upsert subscription in Supabase
    const { error } = await supabase
      .from("profiles")
      .upsert(
        { email, is_subscribed: true },
        { onConflict: "email" } // ensures unique email rows
      );

    if (error) {
      console.error("❌ Error upserting Supabase:", error);
      return { statusCode: 500, body: "Supabase update failed" };
    }

    console.log(`✅ Subscription activated for ${email}`);
  }

  // ✅ Handle subscription deleted / canceled
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;

    try {
      const customer = await stripe.customers.retrieve(subscription.customer);
      const email = customer.email;

      const { error } = await supabase
        .from("profiles")
        .update({ is_subscribed: false })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription canceled for ${email}`);
    } catch (err) {
      console.error("❌ Error retrieving customer:", err.message);
      return { statusCode: 500, body: "Customer fetch failed" };
    }
  }

  return { statusCode: 200, body: "success" };
};



