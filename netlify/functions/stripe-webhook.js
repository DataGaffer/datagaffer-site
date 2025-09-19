// netlify/functions/stripe-webhook.js
const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

// ✅ Tell Netlify not to parse JSON body
exports.config = {
  bodyParser: false,
};

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  const sig = event.headers["stripe-signature"];
  let stripeEvent;

  try {
    // ✅ Construct event using raw body buffer
    stripeEvent = stripe.webhooks.constructEvent(
      Buffer.from(event.body), // raw body buffer
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("❌ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("✅ Verified event:", stripeEvent.type);

  // ✅ Handle checkout session completed
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;
    const email = session.customer_details?.email;

    if (!email) {
      console.error("⚠️ No email found in session");
      return { statusCode: 400, body: "No email found" };
    }

    const { error } = await supabase
      .from("profiles")
      .update({ is_subscribed: true })
      .eq("email", email);

    if (error) {
      console.error("❌ Error updating Supabase:", error);
      return { statusCode: 500, body: "Supabase update failed" };
    }

    console.log(`✅ Subscription activated for ${email}`);
  }

  // ✅ Handle subscription canceled
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;

    try {
      const customer = await stripe.customers.retrieve(subscription.customer);
      const email = customer.email;

      if (email) {
        const { error } = await supabase
          .from("profiles")
          .update({ is_subscribed: false })
          .eq("email", email);

        if (error) {
          console.error("❌ Error updating Supabase:", error);
          return { statusCode: 500, body: "Supabase update failed" };
        }

        console.log(`✅ Subscription canceled for ${email}`);
      }
    } catch (err) {
      console.error("❌ Failed to retrieve customer:", err.message);
      return { statusCode: 500, body: "Stripe customer fetch failed" };
    }
  }

  return { statusCode: 200, body: "success" };
};


