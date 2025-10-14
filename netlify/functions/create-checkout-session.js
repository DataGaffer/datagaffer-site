const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);

exports.handler = async (event) => {
  try {
    const { plan, email } = JSON.parse(event.body);

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

    // ✅ Create checkout session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      subscription_data: {
        trial_period_days: 7, // Optional free trial
      },
      customer_email: email, // Links Stripe to Supabase user email
      success_url: successUrl,
      cancel_url: `${process.env.SITE_URL}/subscribe.html`,
    });

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





