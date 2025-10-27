const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  try {
    const { plan, email } = JSON.parse(event.body);

    if (!email) throw new Error("Missing email");

    // ✅ 1️⃣ Check Supabase for previous trial usage
    const { data: profile, error } = await supabase
      .from("profiles")
      .select("trial_used")
      .eq("email", email.toLowerCase())
      .maybeSingle();

    if (error) throw error;

    const userHasUsedTrial = profile?.trial_used === true;

    // ✅ 2️⃣ Configure pricing and redirect URLs
    let priceId;
    let successUrl;

    if (plan === "monthly") {
      priceId = process.env.STRIPE_PRICE_ID_MONTHLY;
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "yearly") {
      priceId = process.env.STRIPE_PRICE_ID_YEARLY;
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else {
      throw new Error("Invalid plan selected");
    }

    // ✅ 3️⃣ Conditionally include trial only for first-time users
    const subscriptionData = userHasUsedTrial
      ? {} // No free trial
      : { trial_period_days: 7 }; // First-time trial

    // ✅ 4️⃣ Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      subscription_data: subscriptionData,
      customer_email: email,
      success_url: successUrl,
      cancel_url: `${process.env.SITE_URL}/subscribe.html`,
    });

    if (!session.url) throw new Error("No checkout URL returned");

    return {
      statusCode: 200,
      body: JSON.stringify({ url: session.url }),
    };
  } catch (error) {
    console.error("❌ Stripe Checkout Error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};







