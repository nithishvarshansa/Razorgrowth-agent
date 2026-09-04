import { verifyTestPayment } from './api'

export async function openTestCheckout(checkout) {
  await new Promise((resolve, reject) => {
    if (window.Razorpay) return resolve()
    const script=document.createElement('script'); script.src='https://checkout.razorpay.com/v1/checkout.js'; script.onload=resolve; script.onerror=()=>reject(new Error('Unable to load Test Mode checkout.')); document.head.appendChild(script)
  })
  return new Promise((resolve, reject) => new window.Razorpay({key:checkout.key_id,order_id:checkout.razorpay_order_id,amount:checkout.amount,currency:checkout.currency,name:'RazorGrowth Agent',description:'DEMO / TEST DATA',modal:{ondismiss:()=>reject(new Error('Test checkout was cancelled.'))},handler:async response=>{try{resolve(await verifyTestPayment(response))}catch(error){reject(error)}}}).open())
}
